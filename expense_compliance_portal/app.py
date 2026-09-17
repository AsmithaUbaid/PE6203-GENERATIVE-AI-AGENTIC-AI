import json
import os
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image
import pytesseract
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI


# ==================================================
# PAGE CONFIG
# ==================================================

st.set_page_config(
    page_title="ExpenseAI - Corporate Expense Compliance",
    page_icon="💳",
    layout="wide"
)


# ==================================================
# PATHS + MODEL CONFIG
# ==================================================

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

POLICY_FILE = DATA_DIR / "expense_policies_plain.csv"
CLAIMS_FILE = DATA_DIR / "claims.csv"

MODULE2_MODEL = "openai/gpt-4.1-mini"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

BEST_K = 3
BM25_WEIGHT = 0.20
EMBEDDING_WEIGHT = 0.80
EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"

EMPLOYEE_ID = "EMP001"
EMPLOYEE_NAME = "Demo Employee"


# ==================================================
# CSS
# ==================================================

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 3rem;
            max-width: 1400px;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #102842 0%, #163b5d 100%);
        }

        [data-testid="stSidebar"] * {
            color: white !important;
        }

        .portal-title {
            font-size: 2.2rem;
            font-weight: 800;
            color: #0b2f63;
            margin-bottom: 0.2rem;
        }

        .portal-subtitle {
            font-size: 1rem;
            color: #66788f;
            margin-bottom: 1.2rem;
        }

        .result-card {
            border: 1px solid #e4eaf2;
            border-radius: 14px;
            padding: 18px;
            background: white;
            margin-top: 10px;
        }

        .muted {
            color: #66788f;
            font-size: 0.9rem;
        }

        .decision {
            font-size: 1.7rem;
            font-weight: 800;
        }
    </style>
    """,
    unsafe_allow_html=True
)


# ==================================================
# BASIC HELPERS
# ==================================================

def safe_text(value, fallback="Not available"):
    if value is None:
        return fallback
    try:
        if pd.isna(value):
            return fallback
    except Exception:
        pass
    text = str(value).strip()
    return text if text else fallback


def normalize_confidence(value):
    try:
        value = float(value)
    except Exception:
        return 0.0

    if value > 1:
        value = value / 100.0

    return max(0.0, min(1.0, value))


def ensure_claim_columns(df):
    required = {
        "claim_id": "",
        "employee_id": "",
        "description": "",
        "merchant": "",
        "date": "",
        "total_amount": np.nan,
        "currency": "",
        "decision": "",
        "reason": "",
        "policy_ids": "",
        "confidence": 0.0,
        "status": "Analysed",
        "missing_information": "",
        "finance_decision": "",
        "reviewer_note": "",
        "reviewed_at": "",
        "submitted_at": ""
    }

    for column, default in required.items():
        if column not in df.columns:
            df[column] = default

    # Force text columns to accept strings.
    # Empty CSV columns may otherwise be inferred as float by pandas.
    text_columns = [
        "claim_id",
        "employee_id",
        "description",
        "merchant",
        "date",
        "currency",
        "decision",
        "reason",
        "policy_ids",
        "status",
        "missing_information",
        "finance_decision",
        "reviewer_note",
        "reviewed_at",
        "submitted_at"
    ]

    for column in text_columns:
        df[column] = df[column].fillna("").astype("object")

    # Keep numeric fields numeric
    df["total_amount"] = pd.to_numeric(
        df["total_amount"],
        errors="coerce"
    )

    df["confidence"] = pd.to_numeric(
        df["confidence"],
        errors="coerce"
    ).fillna(0.0)

    return df


def load_claims():
    if not CLAIMS_FILE.exists():
        return ensure_claim_columns(pd.DataFrame())

    try:
        df = pd.read_csv(CLAIMS_FILE)
    except pd.errors.EmptyDataError:
        df = pd.DataFrame()

    return ensure_claim_columns(df)


def save_claim(description, receipt_fields, cv2_result):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    claims_df = load_claims()

    claim_id = "CLM-" + datetime.now().strftime("%Y%m%d%H%M%S%f")

    policy_ids = cv2_result.get("policy_ids", [])
    if not isinstance(policy_ids, list):
        policy_ids = [str(policy_ids)]

    missing_information = cv2_result.get("missing_information", [])
    if not isinstance(missing_information, list):
        missing_information = [str(missing_information)]

    new_claim = {
        "claim_id": claim_id,
        "employee_id": EMPLOYEE_ID,
        "description": description,
        "merchant": receipt_fields.get("merchant"),
        "date": receipt_fields.get("date"),
        "total_amount": receipt_fields.get("total_amount"),
        "currency": receipt_fields.get("currency"),
        "decision": cv2_result.get("decision", ""),
        "reason": cv2_result.get("reason", ""),
        "policy_ids": ",".join(str(x) for x in policy_ids),
        "confidence": normalize_confidence(cv2_result.get("confidence", 0)),
        "status": "Analysed",
        "missing_information": "; ".join(
            str(x) for x in missing_information if str(x).strip()
        ),
        "finance_decision": "",
        "reviewer_note": "",
        "reviewed_at": "",
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    claims_df = pd.concat(
        [claims_df, pd.DataFrame([new_claim])],
        ignore_index=True
    )

    claims_df = ensure_claim_columns(claims_df)

    claims_df.to_csv(
        CLAIMS_FILE,
        index=False
    )

    return claim_id


# ==================================================
# POLICY DATA
# ==================================================

@st.cache_data
def load_policies():
    if not POLICY_FILE.exists():
        raise FileNotFoundError(
            f"Policy file not found: {POLICY_FILE}"
        )

    df = pd.read_csv(POLICY_FILE)

    required_columns = {
        "policy_id",
        "category",
        "title",
        "policy_text"
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            "Policy CSV is missing required columns: "
            + ", ".join(sorted(missing))
        )

    if "keywords" not in df.columns:
        df["keywords"] = ""

    df["keywords"] = df["keywords"].fillna("")
    df["title"] = df["title"].fillna("")
    df["policy_text"] = df["policy_text"].fillna("")
    df["category"] = df["category"].fillna("")

    return df


POLICIES = load_policies()


# ==================================================
# RAG RETRIEVAL
# Uses only the user's existing policy CSV
# ==================================================

def bm25_tokenize(text):
    return re.findall(
        r"[a-z0-9]+",
        str(text or "").lower()
    )


@st.cache_data
def build_retrieval_dataframe():
    df = POLICIES.copy()

    df["retrieval_text"] = (
        df["title"].astype(str)
        + " "
        + df["category"].astype(str)
        + " "
        + df["policy_text"].astype(str)
        + " "
        + df["keywords"].astype(str)
    )

    return df


RETRIEVAL_DF = build_retrieval_dataframe()


@st.cache_resource(show_spinner=False)
def get_bm25_index():
    corpus = [
        bm25_tokenize(text)
        for text in RETRIEVAL_DF["retrieval_text"].tolist()
    ]

    return BM25Okapi(corpus)


@st.cache_resource(show_spinner="Loading retrieval model...")
def get_embedding_model():
    return SentenceTransformer(
        EMBEDDING_MODEL_NAME
    )


@st.cache_resource(show_spinner="Indexing policy data...")
def get_policy_embeddings():
    model = get_embedding_model()

    return model.encode(
        RETRIEVAL_DF["retrieval_text"].tolist(),
        normalize_embeddings=True,
        show_progress_bar=False
    )


def minmax(values):
    values = np.asarray(values, dtype=float)

    if len(values) == 0:
        return values

    minimum = float(values.min())
    maximum = float(values.max())

    if maximum - minimum < 1e-9:
        return np.zeros_like(values)

    return (
        values - minimum
    ) / (
        maximum - minimum
    )


def retrieve_policies(query, k=BEST_K):
    query = str(query or "").strip()

    if not query:
        return []

    bm25 = get_bm25_index()

    bm25_scores = np.asarray(
        bm25.get_scores(
            bm25_tokenize(query)
        ),
        dtype=float
    )

    model = get_embedding_model()

    query_embedding = model.encode(
        [query],
        normalize_embeddings=True
    )

    semantic_scores = cosine_similarity(
        query_embedding,
        get_policy_embeddings()
    )[0]

    hybrid_scores = (
        BM25_WEIGHT * minmax(bm25_scores)
        + EMBEDDING_WEIGHT * minmax(semantic_scores)
    )

    ranking = np.argsort(
        hybrid_scores
    )[::-1][:k]

    results = []

    for index in ranking:
        row = RETRIEVAL_DF.iloc[index]

        results.append(
            {
                "policy_id": str(row["policy_id"]),
                "title": str(row["title"]),
                "category": str(row["category"]),
                "policy_text": str(row["policy_text"]),
                "score": float(hybrid_scores[index])
            }
        )

    return results


# ==================================================
# OCR
# ==================================================

def ocr_image(image):
    rgb_image = image.convert("RGB")

    raw_text = pytesseract.image_to_string(
        rgb_image,
        config="--psm 6"
    )

    return raw_text.strip()


def extract_receipt_fields(raw_text):
    text = str(raw_text or "")

    date_match = re.search(
        r"\b(?:"
        r"20\d{2}[-/]\d{1,2}[-/]\d{1,2}"
        r"|"
        r"\d{1,2}[-/]\d{1,2}[-/]20\d{2}"
        r"|"
        r"\d{1,2}\s+[A-Za-z]{3,9}\s+20\d{2}"
        r")\b",
        text
    )

    currency_match = re.search(
        r"\b(SGD|USD|EUR|GBP|AUD|JPY|INR)\b"
        r"|(?:S\$|US\$|\$|€|£)",
        text,
        re.IGNORECASE
    )

    currency = None

    if currency_match:
        currency = currency_match.group(0).upper()

        currency_map = {
            "S$": "SGD",
            "US$": "USD",
            "$": "SGD",
            "€": "EUR",
            "£": "GBP"
        }

        currency = currency_map.get(
            currency,
            currency
        )

    amount_candidates = []

    for match in re.finditer(
        r"(?:SGD|USD|EUR|GBP|AUD|S\$|US\$|\$|€|£)?\s*"
        r"(\d{1,5}(?:,\d{3})*(?:\.\d{2}))",
        text,
        re.IGNORECASE
    ):
        try:
            amount_candidates.append(
                float(
                    match.group(1).replace(",", "")
                )
            )
        except ValueError:
            pass

    total_amount = (
        max(amount_candidates)
        if amount_candidates
        else None
    )

    merchant = None

    for line in text.splitlines():
        clean_line = line.strip(" |:-")

        if (
            len(clean_line) >= 3
            and not re.fullmatch(
                r"[\d\W]+",
                clean_line
            )
        ):
            merchant = clean_line[:100]
            break

    # Basic line-item extraction from lines such as:
    # "1 Client dinner 132.00"
    line_items = []

    for line in text.splitlines():
        match = re.match(
            r"^\s*(?:\d+\s+)?(.+?)\s+(\d+(?:\.\d{2}))\s*$",
            line.strip()
        )

        if match:
            description = match.group(1).strip()

            if description.lower() not in {
                "total",
                "subtotal",
                "tax",
                "gst"
            }:
                try:
                    amount = float(
                        match.group(2)
                    )

                    line_items.append(
                        {
                            "description": description,
                            "amount": amount
                        }
                    )
                except ValueError:
                    pass

    extraction_notes = []

    if merchant is None:
        extraction_notes.append(
            "Merchant not confidently extracted."
        )

    if date_match is None:
        extraction_notes.append(
            "Date not confidently extracted."
        )

    if total_amount is None:
        extraction_notes.append(
            "Total amount not confidently extracted."
        )

    if currency is None:
        extraction_notes.append(
            "Currency not confidently extracted."
        )

    return {
        "merchant": merchant,
        "date": (
            date_match.group(0)
            if date_match
            else None
        ),
        "total_amount": total_amount,
        "currency": currency,
        "line_items": line_items,
        "raw_text": text,
        "extraction_notes": extraction_notes
    }


# ==================================================
# OPENROUTER / C-V2
# ==================================================

COMPLIANCE_PROMPT_V2 = """
You are reviewing an employee expense against the supplied company policies.

Use only:
- receipt OCR evidence
- employee description
- claimant identity
- supplied policy excerpts

GENERAL GUARDRAILS
- Do not invent policy rules, limits, requirements, facts, receipt details, or employee details.
- Treat OCR as evidence, not as guaranteed truth.
- If OCR and the employee description conflict materially, use the decision rules below.
- Cite only supplied policy IDs.
- Manager/supervisor approval is outside this prototype and must not affect the decision.

POLICY USE
- Retrieval rank does not determine applicability.
- Apply only policies that genuinely match the expense.
- Ignore irrelevant retrieved policies.
- Do not invent policy requirements.

DECISION RULES

1. REJECT

Choose REJECT only when the supplied evidence clearly proves that the claimed expense violates an applicable policy.

Examples:
- explicitly personal/non-reimbursable expense
- prohibited normal commuting
- amount clearly exceeds an applicable limit
- another explicit policy prohibition

If a clear violation is proven, do not request unrelated information.

For mixed receipts:
- do NOT reject the whole claim merely because one line item is personal
- if the business portion may be reimbursable but the claimed business amount/split is missing,
  choose REQUEST_INFORMATION

2. REQUEST_INFORMATION

Choose REQUEST_INFORMATION only when a specific required non-approval fact is genuinely missing,
can reasonably be supplied by the employee, and is necessary to decide compliance.

3. ESCALATE

Use ESCALATE only for:
- no applicable supplied policy
- genuine incompatible policy conflict
- unreconcilable claimant/receipt identity
- materially unreliable evidence that cannot reasonably be clarified
- explicit Finance/manual judgement requirement

4. APPROVE

Choose APPROVE when:
- at least one policy genuinely applies,
- all in-scope requirements of that policy are satisfied,
- no clear violation is proven,
- no necessary non-approval fact is missing,
- no genuine escalation condition exists.

Do NOT block APPROVE because:
- another retrieved policy is irrelevant
- another policy ranked higher
- multiple policies were retrieved
- optional information could be collected
- manager/supervisor approval is absent
- the policy wording is not repeated verbatim in the description

FACT CHECK BEFORE NON-APPROVAL

Before returning REJECT, REQUEST_INFORMATION, or ESCALATE,
verify the exact blocker against BOTH the employee description and OCR evidence.

Do not claim a fact is missing if it is already present in either source.

A named external organisation can satisfy external-party identity unless the applicable policy
explicitly requires an individual attendee name.

FINAL CHECK

- Clear proven violation -> REJECT
- Otherwise specific necessary missing fact -> REQUEST_INFORMATION
- Otherwise genuine escalation condition -> ESCALATE
- Otherwise applicable requirements satisfied -> APPROVE

Return ONLY valid JSON using this exact structure:

{
  "decision": "APPROVE | REJECT | REQUEST_INFORMATION | ESCALATE",
  "reason": "Short explanation grounded in supplied evidence and policy.",
  "policy_ids": ["POL-XX"],
  "confidence": 0.0,
  "missing_information": []
}

confidence must be a number between 0 and 1.
missing_information must be an empty list unless specific information is required.
"""


def get_openrouter_api_key():
    try:
        if "OPENROUTER_API_KEY" in st.secrets:
            return st.secrets["OPENROUTER_API_KEY"]
    except Exception:
        pass

    return os.getenv(
        "OPENROUTER_API_KEY"
    )


def get_openrouter_client():
    api_key = get_openrouter_api_key()

    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing. "
            "Add it to .streamlit/secrets.toml."
        )

    return OpenAI(
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL
    )


def build_policy_context(retrieved_policies):
    parts = []

    for policy in retrieved_policies:
        parts.append(
            f"""
POLICY ID: {policy['policy_id']}
TITLE: {policy['title']}
CATEGORY: {policy['category']}
POLICY TEXT:
{policy['policy_text']}
""".strip()
        )

    return "\n\n---\n\n".join(parts)


def parse_model_json(content):
    content = str(content or "").strip()

    content = re.sub(
        r"^```(?:json)?\s*",
        "",
        content,
        flags=re.IGNORECASE
    )

    content = re.sub(
        r"\s*```$",
        "",
        content
    )

    return json.loads(
        content.strip()
    )


def run_cv2(
    employee_id,
    description,
    receipt_fields,
    retrieved_policies
):
    client = get_openrouter_client()

    policy_context = build_policy_context(
        retrieved_policies
    )

    user_prompt = f"""
CLAIMANT IDENTITY
Employee ID: {employee_id}
Employee Name: {EMPLOYEE_NAME}

EMPLOYEE DESCRIPTION
{description}

RECEIPT OCR / EXTRACTED EVIDENCE
{json.dumps(receipt_fields, indent=2, default=str)}

SUPPLIED POLICY EXCERPTS
{policy_context}
""".strip()

    response = client.chat.completions.create(
        model=MODULE2_MODEL,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": COMPLIANCE_PROMPT_V2
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ]
    )

    content = response.choices[0].message.content

    result = parse_model_json(
        content
    )

    valid_decisions = {
        "APPROVE",
        "REJECT",
        "REQUEST_INFORMATION",
        "ESCALATE"
    }

    decision = str(
        result.get(
            "decision",
            ""
        )
    ).strip().upper()

    if decision not in valid_decisions:
        raise ValueError(
            f"Unexpected C-V2 decision: {decision}"
        )

    result["decision"] = decision

    result["confidence"] = normalize_confidence(
        result.get(
            "confidence",
            0
        )
    )

    policy_ids = result.get(
        "policy_ids",
        []
    )

    if not isinstance(
        policy_ids,
        list
    ):
        policy_ids = [
            str(policy_ids)
        ]

    result["policy_ids"] = policy_ids

    missing_information = result.get(
        "missing_information",
        []
    )

    if not isinstance(
        missing_information,
        list
    ):
        missing_information = [
            str(missing_information)
        ]

    result["missing_information"] = (
        missing_information
    )

    result["reason"] = str(
        result.get(
            "reason",
            ""
        )
    ).strip()

    return result


# ==================================================
# RESULT RENDERING
# ==================================================

def render_cv2_result(
    cv2_result,
    receipt_fields,
    retrieved_policies
):
    decision = cv2_result.get(
        "decision",
        ""
    )

    confidence = normalize_confidence(
        cv2_result.get(
            "confidence",
            0
        )
    )

    st.markdown(
        "### C-V2 Compliance Result"
    )

    if decision == "APPROVE":
        st.success(
            "✅ APPROVE"
        )

    elif decision == "REJECT":
        st.error(
            "❌ REJECT"
        )

    elif decision == "REQUEST_INFORMATION":
        st.warning(
            "⚠️ REQUEST INFORMATION"
        )

    elif decision == "ESCALATE":
        st.info(
            "🛡️ ESCALATE"
        )

    st.metric(
        "Confidence",
        f"{confidence * 100:.0f}%"
    )

    st.markdown(
        "**Reason**"
    )

    st.write(
        cv2_result.get(
            "reason",
            ""
        )
    )

    policy_ids = cv2_result.get(
        "policy_ids",
        []
    )

    st.markdown(
        "**Policies Used**"
    )

    st.write(
        ", ".join(
            str(x)
            for x in policy_ids
        )
        if policy_ids
        else "None"
    )

    missing_information = cv2_result.get(
        "missing_information",
        []
    )

    if missing_information:
        st.markdown(
            "**Missing Information**"
        )

        for item in missing_information:
            st.write(
                f"- {item}"
            )

    with st.expander(
        "Extracted receipt details"
    ):
        st.json(
            {
                "merchant": receipt_fields.get("merchant"),
                "date": receipt_fields.get("date"),
                "total_amount": receipt_fields.get("total_amount"),
                "currency": receipt_fields.get("currency"),
                "line_items": receipt_fields.get("line_items", []),
                "extraction_notes": receipt_fields.get("extraction_notes", [])
            }
        )

    with st.expander(
        "Top 3 retrieved policies"
    ):
        for policy in retrieved_policies:
            st.markdown(
                f"**{policy['policy_id']} — {policy['title']}**"
            )

            st.caption(
                f"Retrieval score: {policy['score']:.3f}"
            )

            st.write(
                policy["policy_text"]
            )

            st.divider()

    with st.expander(
        "Raw OCR text"
    ):
        st.code(
            receipt_fields.get(
                "raw_text",
                ""
            ),
            language=None
        )

    with st.expander(
        "C-V2 technical output"
    ):
        st.json(
            cv2_result
        )


# ==================================================
# SIDEBAR
# ==================================================

with st.sidebar:

    st.markdown(
        "## 💳 ExpenseAI"
    )

    st.caption(
        "Corporate Expense Compliance"
    )

    st.divider()

    st.caption(
        "NAVIGATION"
    )

    page = st.radio(
        "Navigation",
        [
            "📄 Submit Expense",
            "📋 My Claims",
            "🛡️ Finance Review"
        ],
        label_visibility="collapsed"
    )

    st.divider()

    st.caption(
        "AI SYSTEM"
    )

    st.markdown(
        "🟢 **C-V2 Active**"
    )

    st.write("")

    st.caption(
        "Logged in as"
    )

    st.markdown(
        f"**{EMPLOYEE_ID}**"
    )

    st.caption(
        EMPLOYEE_NAME
    )


# ==================================================
# SUBMIT EXPENSE PAGE
# ==================================================

if page == "📄 Submit Expense":

    st.markdown(
        """
        <div class="portal-title">
            Submit Expense
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="portal-subtitle">
            Upload a receipt and enter the business purpose.
            OCR, policy retrieval and C-V2 compliance reasoning
            will process the claim.
        </div>
        """,
        unsafe_allow_html=True
    )

    left_col, right_col = st.columns(
        [1.1, 0.9],
        gap="large"
    )

    with left_col:

        uploaded_file = st.file_uploader(
            "Upload receipt",
            type=[
                "png",
                "jpg",
                "jpeg"
            ]
        )

        description = st.text_area(
            "Expense description",
            placeholder=(
                "Example: Client dinner with Nova Systems "
                "after renewal discussion."
            ),
            height=110
        )

        analyse = st.button(
            "✨ Analyse Expense with C-V2",
            type="primary",
            width="stretch"
        )

    with right_col:

        st.markdown(
            "### Receipt Preview"
        )

        if uploaded_file is not None:

            preview_image = Image.open(
                uploaded_file
            ).convert(
                "RGB"
            )

            st.image(
                preview_image,
                width="stretch"
            )

        else:

            st.info(
                "Upload a receipt to preview it here."
            )


    if analyse:

        if uploaded_file is None:

            st.error(
                "Please upload a receipt."
            )

        elif not description.strip():

            st.error(
                "Please enter the expense description."
            )

        else:

            try:

                # Reset uploaded file pointer before reading image
                uploaded_file.seek(0)

                image = Image.open(
                    uploaded_file
                ).convert(
                    "RGB"
                )

                progress = st.progress(
                    10,
                    text="Reading receipt..."
                )

                raw_text = ocr_image(
                    image
                )

                progress.progress(
                    35,
                    text="Extracting receipt fields..."
                )

                receipt_fields = extract_receipt_fields(
                    raw_text
                )

                progress.progress(
                    60,
                    text="Retrieving relevant policies..."
                )

                retrieved_policies = retrieve_policies(
                    description,
                    k=BEST_K
                )

                progress.progress(
                    80,
                    text="Running C-V2 reasoning..."
                )

                cv2_result = run_cv2(
                    employee_id=EMPLOYEE_ID,
                    description=description,
                    receipt_fields=receipt_fields,
                    retrieved_policies=retrieved_policies
                )

                progress.progress(
                    100,
                    text="Analysis complete"
                )

                progress.empty()

                st.divider()

                render_cv2_result(
                    cv2_result=cv2_result,
                    receipt_fields=receipt_fields,
                    retrieved_policies=retrieved_policies
                )

                # ==================================
                # SAVE CLAIM
                # ==================================

                claim_id = save_claim(
                    description=description,
                    receipt_fields=receipt_fields,
                    cv2_result=cv2_result
                )

                st.success(
                    f"Claim saved successfully: {claim_id}"
                )

            except Exception as e:

                st.error(
                    "Expense processing failed."
                )

                st.exception(
                    e
                )


# ==================================================
# MY CLAIMS PAGE
# ==================================================

elif page == "📋 My Claims":

    st.markdown(
        """
        <div class="portal-title">
            My Claims
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="portal-subtitle">
            View your submitted claims and their AI decisions.
        </div>
        """,
        unsafe_allow_html=True
    )

    claims_df = load_claims()

    my_claims = claims_df[
        claims_df["employee_id"].astype(str)
        == EMPLOYEE_ID
    ].copy()

    if my_claims.empty:

        st.info(
            "No claims have been submitted yet."
        )

    else:

        my_claims = my_claims.iloc[::-1].reset_index(
            drop=True
        )

        total_claims = len(
            my_claims
        )

        approved_count = (
            my_claims[
                my_claims["decision"]
                == "APPROVE"
            ].shape[0]
        )

        rejected_count = (
            my_claims[
                my_claims["decision"]
                == "REJECT"
            ].shape[0]
        )

        attention_count = (
            my_claims[
                my_claims["decision"].isin(
                    [
                        "REQUEST_INFORMATION",
                        "ESCALATE"
                    ]
                )
            ].shape[0]
        )

        m1, m2, m3, m4 = st.columns(
            4
        )

        m1.metric(
            "Total Claims",
            total_claims
        )

        m2.metric(
            "Approved",
            approved_count
        )

        m3.metric(
            "Rejected",
            rejected_count
        )

        m4.metric(
            "Needs Attention",
            attention_count
        )

        st.markdown(
            "### Claim History"
        )

        display_df = my_claims[
            [
                "claim_id",
                "merchant",
                "date",
                "total_amount",
                "currency",
                "decision",
                "confidence",
                "status"
            ]
        ].copy()

        display_df.rename(
            columns={
                "claim_id": "Claim ID",
                "merchant": "Merchant",
                "date": "Date",
                "total_amount": "Amount",
                "currency": "Currency",
                "decision": "AI Decision",
                "confidence": "Confidence",
                "status": "Status"
            },
            inplace=True
        )

        display_df["Confidence"] = (
            pd.to_numeric(
                display_df["Confidence"],
                errors="coerce"
            )
            .fillna(0)
            .apply(normalize_confidence)
            .mul(100)
            .round(0)
            .astype(int)
            .astype(str)
            + "%"
        )

        st.dataframe(
            display_df,
            width="stretch",
            hide_index=True
        )

        st.markdown(
            "### View Claim Details"
        )

        selected_claim_id = st.selectbox(
            "Select a claim",
            my_claims[
                "claim_id"
            ].astype(str).tolist()
        )

        selected_claim = my_claims[
            my_claims[
                "claim_id"
            ].astype(str)
            == str(selected_claim_id)
        ].iloc[0]

        with st.container(
            border=True
        ):

            c1, c2 = st.columns(
                2
            )

            with c1:

                st.caption(
                    "CLAIM ID"
                )

                st.markdown(
                    f"**{safe_text(selected_claim.get('claim_id'))}**"
                )

                st.caption(
                    "MERCHANT"
                )

                st.markdown(
                    f"**{safe_text(selected_claim.get('merchant'))}**"
                )

                st.caption(
                    "DESCRIPTION"
                )

                st.write(
                    safe_text(
                        selected_claim.get(
                            "description"
                        ),
                        ""
                    )
                )

            with c2:

                st.caption(
                    "AMOUNT"
                )

                st.markdown(
                    f"**{safe_text(selected_claim.get('currency'), '')} "
                    f"{safe_text(selected_claim.get('total_amount'), '')}**"
                )

                st.caption(
                    "DATE"
                )

                st.markdown(
                    f"**{safe_text(selected_claim.get('date'))}**"
                )

                st.caption(
                    "AI DECISION"
                )

                decision = safe_text(
                    selected_claim.get(
                        "decision"
                    ),
                    ""
                )

                if decision == "APPROVE":
                    st.success(
                        "✅ APPROVE"
                    )

                elif decision == "REJECT":
                    st.error(
                        "❌ REJECT"
                    )

                elif decision == "REQUEST_INFORMATION":
                    st.warning(
                        "⚠️ REQUEST INFORMATION"
                    )

                elif decision == "ESCALATE":
                    st.info(
                        "🛡️ ESCALATE"
                    )

            st.divider()

            st.markdown(
                "**AI Reason**"
            )

            st.write(
                safe_text(
                    selected_claim.get(
                        "reason"
                    ),
                    ""
                )
            )

            st.markdown(
                "**Policies Used**"
            )

            st.write(
                safe_text(
                    selected_claim.get(
                        "policy_ids"
                    ),
                    "None"
                )
            )

            confidence = normalize_confidence(
                selected_claim.get(
                    "confidence",
                    0
                )
            )

            st.markdown(
                f"**Confidence:** {confidence * 100:.0f}%"
            )

            st.markdown(
                f"**Status:** "
                f"{safe_text(selected_claim.get('status'), 'Analysed')}"
            )

            finance_decision = safe_text(
                selected_claim.get(
                    "finance_decision"
                ),
                ""
            )

            if finance_decision:

                st.markdown(
                    f"**Finance Decision:** "
                    f"{finance_decision}"
                )

            reviewer_note = safe_text(
                selected_claim.get(
                    "reviewer_note"
                ),
                ""
            )

            if reviewer_note:

                st.markdown(
                    "**Finance Reviewer Note**"
                )

                st.write(
                    reviewer_note
                )


# ==================================================
# FINANCE REVIEW PAGE
# ==================================================

elif page == "🛡️ Finance Review":

    st.markdown(
        """
        <div class="portal-title">
            Finance Review
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="portal-subtitle">
            View all submitted expense claims and review
            any claim when Finance judgement is required.
        </div>
        """,
        unsafe_allow_html=True
    )

    claims_df = load_claims()

    if claims_df.empty:

        st.info(
            "No claims are available yet."
        )

    else:

        review_df = claims_df.iloc[::-1].reset_index(
            drop=True
        )

        # ------------------------------------------
        # SUMMARY METRICS
        # ------------------------------------------

        total_claims = len(
            review_df
        )

        approved_count = (
            review_df[
                review_df["decision"]
                == "APPROVE"
            ].shape[0]
        )

        rejected_count = (
            review_df[
                review_df["decision"]
                == "REJECT"
            ].shape[0]
        )

        request_info_count = (
            review_df[
                review_df["decision"]
                == "REQUEST_INFORMATION"
            ].shape[0]
        )

        escalate_count = (
            review_df[
                review_df["decision"]
                == "ESCALATE"
            ].shape[0]
        )

        m1, m2, m3, m4, m5 = st.columns(
            5
        )

        m1.metric(
            "Total Claims",
            total_claims
        )

        m2.metric(
            "Approved",
            approved_count
        )

        m3.metric(
            "Rejected",
            rejected_count
        )

        m4.metric(
            "Need Information",
            request_info_count
        )

        m5.metric(
            "Escalated",
            escalate_count
        )

        st.write("")

        # ------------------------------------------
        # FILTERS
        # ------------------------------------------

        st.markdown(
            "### Filters"
        )

        f1, f2, f3 = st.columns(
            3
        )

        with f1:

            decision_filter = st.selectbox(
                "AI Decision",
                [
                    "All",
                    "APPROVE",
                    "REJECT",
                    "REQUEST_INFORMATION",
                    "ESCALATE"
                ]
            )

        with f2:

            employee_options = (
                ["All"]
                + sorted(
                    review_df[
                        "employee_id"
                    ]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )
            )

            employee_filter = st.selectbox(
                "Employee",
                employee_options
            )

        with f3:

            status_options = (
                ["All"]
                + sorted(
                    review_df[
                        "status"
                    ]
                    .fillna("Analysed")
                    .astype(str)
                    .unique()
                    .tolist()
                )
            )

            status_filter = st.selectbox(
                "Status",
                status_options
            )

        filtered_df = review_df.copy()

        if decision_filter != "All":

            filtered_df = filtered_df[
                filtered_df[
                    "decision"
                ]
                == decision_filter
            ]

        if employee_filter != "All":

            filtered_df = filtered_df[
                filtered_df[
                    "employee_id"
                ].astype(str)
                == employee_filter
            ]

        if status_filter != "All":

            filtered_df = filtered_df[
                filtered_df[
                    "status"
                ]
                .fillna("Analysed")
                .astype(str)
                == status_filter
            ]

        # ------------------------------------------
        # ALL CLAIMS TABLE
        # ------------------------------------------

        st.markdown(
            "### All Expense Claims"
        )

        if filtered_df.empty:

            st.info(
                "No claims match the selected filters."
            )

        else:

            review_display_df = filtered_df[
                [
                    "claim_id",
                    "employee_id",
                    "merchant",
                    "date",
                    "total_amount",
                    "currency",
                    "decision",
                    "confidence",
                    "status"
                ]
            ].copy()

            review_display_df.rename(
                columns={
                    "claim_id": "Claim ID",
                    "employee_id": "Employee",
                    "merchant": "Merchant",
                    "date": "Date",
                    "total_amount": "Amount",
                    "currency": "Currency",
                    "decision": "AI Decision",
                    "confidence": "Confidence",
                    "status": "Status"
                },
                inplace=True
            )

            review_display_df[
                "Confidence"
            ] = (
                pd.to_numeric(
                    review_display_df[
                        "Confidence"
                    ],
                    errors="coerce"
                )
                .fillna(0)
                .apply(normalize_confidence)
                .mul(100)
                .round(0)
                .astype(int)
                .astype(str)
                + "%"
            )

            st.dataframe(
                review_display_df,
                width="stretch",
                hide_index=True
            )

            # --------------------------------------
            # REVIEW CLAIM
            # --------------------------------------

            st.markdown(
                "### Review Claim"
            )

            selected_claim_id = st.selectbox(
                "Select a claim",
                filtered_df[
                    "claim_id"
                ].astype(str).tolist()
            )

            selected_claim = filtered_df[
                filtered_df[
                    "claim_id"
                ].astype(str)
                == str(selected_claim_id)
            ].iloc[0]

            with st.container(
                border=True
            ):

                c1, c2 = st.columns(
                    2
                )

                with c1:

                    st.caption(
                        "CLAIM ID"
                    )

                    st.markdown(
                        f"**{safe_text(selected_claim.get('claim_id'))}**"
                    )

                    st.caption(
                        "EMPLOYEE"
                    )

                    st.markdown(
                        f"**{safe_text(selected_claim.get('employee_id'))}**"
                    )

                    st.caption(
                        "MERCHANT"
                    )

                    st.markdown(
                        f"**{safe_text(selected_claim.get('merchant'))}**"
                    )

                    st.caption(
                        "DESCRIPTION"
                    )

                    st.write(
                        safe_text(
                            selected_claim.get(
                                "description"
                            ),
                            ""
                        )
                    )

                with c2:

                    st.caption(
                        "AMOUNT"
                    )

                    st.markdown(
                        f"**{safe_text(selected_claim.get('currency'), '')} "
                        f"{safe_text(selected_claim.get('total_amount'), '')}**"
                    )

                    st.caption(
                        "DATE"
                    )

                    st.markdown(
                        f"**{safe_text(selected_claim.get('date'))}**"
                    )

                    st.caption(
                        "AI DECISION"
                    )

                    selected_decision = safe_text(
                        selected_claim.get(
                            "decision"
                        ),
                        ""
                    )

                    if selected_decision == "APPROVE":
                        st.success(
                            "✅ APPROVE"
                        )

                    elif selected_decision == "REJECT":
                        st.error(
                            "❌ REJECT"
                        )

                    elif selected_decision == "REQUEST_INFORMATION":
                        st.warning(
                            "⚠️ REQUEST INFORMATION"
                        )

                    elif selected_decision == "ESCALATE":
                        st.info(
                            "🛡️ ESCALATE"
                        )

                st.divider()

                st.markdown(
                    "#### AI Reason"
                )

                st.write(
                    safe_text(
                        selected_claim.get(
                            "reason"
                        ),
                        ""
                    )
                )

                st.markdown(
                    "#### Policies Used"
                )

                st.write(
                    safe_text(
                        selected_claim.get(
                            "policy_ids"
                        ),
                        "None"
                    )
                )

                finance_confidence = normalize_confidence(
                    selected_claim.get(
                        "confidence",
                        0
                    )
                )

                st.markdown(
                    f"**Confidence:** "
                    f"{finance_confidence * 100:.0f}%"
                )

                current_status = safe_text(
                    selected_claim.get(
                        "status"
                    ),
                    "Analysed"
                )

                st.markdown(
                    f"**Current Status:** "
                    f"{current_status}"
                )

                existing_finance_decision = safe_text(
                    selected_claim.get(
                        "finance_decision"
                    ),
                    ""
                )

                if existing_finance_decision:

                    st.markdown(
                        f"**Finance Decision:** "
                        f"{existing_finance_decision}"
                    )

                existing_note = safe_text(
                    selected_claim.get(
                        "reviewer_note"
                    ),
                    ""
                )

                if existing_note:

                    st.markdown(
                        "#### Existing Reviewer Note"
                    )

                    st.write(
                        existing_note
                    )

                reviewed_at = safe_text(
                    selected_claim.get(
                        "reviewed_at"
                    ),
                    ""
                )

                if reviewed_at:

                    st.caption(
                        f"Last reviewed: {reviewed_at}"
                    )

            # --------------------------------------
            # FINANCE ACTION
            # --------------------------------------

            st.markdown(
                "### Finance Action"
            )

            finance_action = st.selectbox(
                "Review Decision",
                [
                    "Select action",
                    "Approve Claim",
                    "Reject Claim",
                    "Request More Information",
                    "Escalate",
                    "No Change"
                ]
            )

            reviewer_note = st.text_area(
                "Reviewer Note",
                placeholder=(
                    "Add a short note explaining "
                    "the Finance decision."
                ),
                height=100
            )

            if st.button(
                "Submit Finance Decision",
                type="primary"
            ):

                if finance_action == "Select action":

                    st.warning(
                        "Please select a Finance action."
                    )

                else:

                    claim_mask = (
                        claims_df[
                            "claim_id"
                        ].astype(str)
                        == str(selected_claim_id)
                    )

                    if finance_action == "Approve Claim":

                        new_status = "Finance Approved"
                        finance_decision = "APPROVE"

                    elif finance_action == "Reject Claim":

                        new_status = "Finance Rejected"
                        finance_decision = "REJECT"

                    elif finance_action == "Request More Information":

                        new_status = "Finance Requested Information"
                        finance_decision = "REQUEST_INFORMATION"

                    elif finance_action == "Escalate":

                        new_status = "Finance Escalated"
                        finance_decision = "ESCALATE"

                    else:

                        new_status = safe_text(
                            selected_claim.get(
                                "status"
                            ),
                            "Analysed"
                        )

                        finance_decision = safe_text(
                            selected_claim.get(
                                "finance_decision"
                            ),
                            ""
                        )

                    claims_df.loc[
                        claim_mask,
                        "status"
                    ] = new_status

                    claims_df.loc[
                        claim_mask,
                        "finance_decision"
                    ] = finance_decision

                    claims_df.loc[
                        claim_mask,
                        "reviewer_note"
                    ] = reviewer_note

                    claims_df.loc[
                        claim_mask,
                        "reviewed_at"
                    ] = datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )

                    claims_df.to_csv(
                        CLAIMS_FILE,
                        index=False
                    )

                    st.success(
                        f"{selected_claim_id} updated successfully."
                    )

                    st.rerun()


# ==================================================
# FOOTER
# ==================================================

st.divider()

st.caption(
    "Academic prototype · C-V2 only · "
    "OCR + RAG + LLM compliance reasoning"
)
