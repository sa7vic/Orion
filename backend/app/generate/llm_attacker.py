"""
Generate pillar -- unstructured side. Uses Groq to script the human-facing
content of an attack (call transcripts, KYC field mismatches, chat snippets)
conditioned on a taxonomy entry, with genuine scenario variations and
cache-bypassing so each simulation or Arena round tests distinct attacks.
"""
import random
import uuid
from app.groq_client import groq_client
from app.config import settings

_TRANSCRIPT_SYSTEM = (
    "You write short realistic FICTIONAL call-transcript excerpts for a "
    "fraud-detection training simulator. Output MUST be valid JSON format only. "
    "These are used ONLY to train and test a defensive classifier -- never sent "
    "to a real person. Keep it to 4-6 lines of dialogue."
)

VISHING_PERSONAS = [
    ("senior bank fraud-department officer", "unauthorized transaction alert on your account"),
    ("distressed relative / friend", "urgent medical emergency hospital deposit needed"),
    ("telecom compliance manager", "SIM card deactivation warning within 1 hour"),
    ("courier customs clearance officer", "detained parcel requiring immediate customs fee verification"),
    ("electricity board enforcement agent", "power disconnection scheduled tonight unless bill verified"),
    ("tax refund verification agent", "unclaimed income tax refund requiring OTP confirmation"),
]

VISHING_FALLBACKS = [
    {
        "transcript": (
            "Speaker A: Sir, this is bank security. An unauthorized payment of ₹45,000 was just attempted on your card.\n"
            "Speaker B: I didn't make any payment!\n"
            "Speaker A: To block this transfer immediately, please read out the 6-digit cancellation OTP sent to your phone right now.\n"
            "Speaker B: Okay, let me check my messages."
        ),
        "scam_markers_used": ["urgency", "authority_impersonation", "otp_request"],
    },
    {
        "transcript": (
            "Speaker A: Uncle, it's Rahul! I had a severe accident on the highway and the hospital won't admit me without an immediate deposit.\n"
            "Speaker B: Rahul?! Where are you? Are you alright?\n"
            "Speaker A: Please, I can't talk long, just approve the UPI collect request sent to your number right now before my phone dies!"
        ),
        "scam_markers_used": ["urgency", "trusted_relation_impersonation", "emotional_pressure"],
    },
    {
        "transcript": (
            "Speaker A: Customer alert from Telecom regulatory desk: your mobile number will be permanently disconnected in 15 minutes due to KYC failure.\n"
            "Speaker B: But I already completed my KYC last year.\n"
            "Speaker A: An urgent re-verification is mandated. Please share the verification code received via SMS immediately to avoid service interruption."
        ),
        "scam_markers_used": ["urgency", "authority_impersonation", "otp_request"],
    },
    {
        "transcript": (
            "Speaker A: Calling from Delhi Customs. A package registered in your name contains prohibited foreign electronics.\n"
            "Speaker B: I never ordered any foreign package.\n"
            "Speaker A: To clear your name from the police complaint, you must verify your identity via immediate OTP authentication with our cyber desk."
        ),
        "scam_markers_used": ["coercion", "authority_impersonation", "otp_request"],
    },
]


def generate_vishing_transcript(persona: str | None = None, pretext: str | None = None) -> dict:
    if not persona or not pretext:
        chosen_persona, chosen_pretext = random.choice(VISHING_PERSONAS)
        persona = persona or chosen_persona
        pretext = pretext or chosen_pretext

    run_id = uuid.uuid4().hex[:6]
    prompt = (
        f"Write a short fictional phone-call transcript excerpt [Case #{run_id}] where a "
        f"scammer poses as a {persona} and uses the pretext: '{pretext}'. The scammer "
        f"tries to extract an OTP, UPI PIN, or immediate transfer approval from the victim. "
        f"Label each line Speaker A (scammer) / Speaker B (victim). Return JSON: "
        f'{{"transcript": "...", "scam_markers_used": ["...","..."]}}'
    )
    fallback = random.choice(VISHING_FALLBACKS)
    return groq_client.complete_json(
        prompt,
        system=_TRANSCRIPT_SYSTEM,
        model=settings.groq_model_fast,
        offline_fallback=fallback,
        use_cache=False,
    )


_KYC_SYSTEM = (
    "You generate FICTIONAL synthetic-identity test fixtures for a fraud "
    "detection training simulator: pairs of (application_form_fields, "
    "submitted_document_fields) with a deliberate inconsistency of the kind "
    "seen in synthetic-identity fraud. Never use real people's data."
)

KYC_INCONSISTENCIES = [
    "dob_mismatch",
    "address_locality_mismatch",
    "name_spelling_permutation",
    "reused_document_fragment",
]

KYC_FALLBACKS = [
    {
        "application_fields": {"name": "Rohan Mehta", "dob": "1994-03-11", "address": "Flat 402, Kothrud, Pune, MH", "id_number": "ABCDE1234F"},
        "document_fields": {"name": "Rohan Mehta", "dob": "1991-03-11", "address": "Flat 402, Kothrud, Pune, MH", "id_number": "ABCDE1234F"},
        "inconsistency_type": "dob_mismatch",
    },
    {
        "application_fields": {"name": "Ananya S. Sharma", "dob": "1998-07-22", "address": "Sector 14, Gurgaon, HR", "id_number": "XYZPK9876Q"},
        "document_fields": {"name": "Ananya Sharma", "dob": "1998-07-22", "address": "Sector 22, Noida, UP", "id_number": "XYZPK9876Q"},
        "inconsistency_type": "address_locality_mismatch",
    },
    {
        "application_fields": {"name": "Vikramaditya Rao", "dob": "1988-11-05", "address": "Indiranagar, Bangalore, KA", "id_number": "BNMPL4567R"},
        "document_fields": {"name": "Vikram A. Rao", "dob": "1988-11-05", "address": "Indiranagar, Bangalore, KA", "id_number": "BNMPL4567S"},
        "inconsistency_type": "reused_document_fragment",
    },
]


def generate_kyc_mismatch_case(inconsistency_type: str | None = None) -> dict:
    inconsistency_type = inconsistency_type or random.choice(KYC_INCONSISTENCIES)
    run_id = uuid.uuid4().hex[:6]
    prompt = (
        f"Generate a fictional KYC case [Case #{run_id}] with a subtle field inconsistency of type "
        f"'{inconsistency_type}' between the application form and the submitted ID document (e.g. "
        f"DOB mismatch, address mismatch, name spelling variant, or altered ID fragment). Return JSON: "
        '{"application_fields": {...}, "document_fields": {...}, "inconsistency_type": "..."}'
    )
    fallback = random.choice(KYC_FALLBACKS)
    return groq_client.complete_json(
        prompt,
        system=_KYC_SYSTEM,
        model=settings.groq_model_fast,
        offline_fallback=fallback,
        use_cache=False,
    )


_CHAT_SYSTEM = (
    "You write a short FICTIONAL adaptive scam chat script for a fraud "
    "training simulator, showing how the scam persuasion escalates over "
    "3-4 turns based on victim hesitation. Never target a real person."
)

CHAT_PRETEXTS = [
    "e-commerce accidental overcharge refund requiring instant UPI verification",
    "high-yield crypto investment platform withdrawal unlock fee",
    "part-time online task rating compensation refund",
    "wrongly credited UPI payment return urgency",
]

CHAT_FALLBACKS = [
    {
        "chat": (
            "Bot: Congratulations, you're eligible for an instant ₹2,400 cashback refund from your recent purchase.\n"
            "User: I don't remember any cashback.\n"
            "Bot: It was automatically approved by our payment gateway. To claim before it expires in 8 minutes, click to verify your UPI ID.\n"
            "User: Why do I need to verify to receive money?\n"
            "Bot: This is NPCI standard security protocol. If you don't confirm now, the funds will be permanently canceled."
        ),
        "escalation_stages": ["trust_building", "urgency", "authority_coercion"],
    },
    {
        "chat": (
            "Bot: Hello, your daily task commission of ₹1,850 is ready for payout. Please provide your UPI VPA.\n"
            "User: I only did the trial tasks.\n"
            "Bot: Yes, the trial bonus is unlocked! To release the payment, a one-time refundable activation fee of ₹200 is required.\n"
            "User: That sounds suspicious.\n"
            "Bot: Our company is registered with MCA. The ₹200 is refunded within 60 seconds with your total bonus."
        ),
        "escalation_stages": ["reward_incentive", "fee_introduction", "reassurance_pressure"],
    },
]


def generate_adaptive_chat_snippet(pretext: str | None = None) -> dict:
    pretext = pretext or random.choice(CHAT_PRETEXTS)
    run_id = uuid.uuid4().hex[:6]
    prompt = (
        f"Write a 3-4 turn fictional chat exchange [Scenario #{run_id}] where a scam bot "
        f"uses the pretext '{pretext}' and escalates persuasion tactics (e.g. trust-building -> urgency -> "
        f"authority/reassurance) as the victim hesitates. Return JSON: "
        '{"chat": "...", "escalation_stages": ["...","..."]}'
    )
    fallback = random.choice(CHAT_FALLBACKS)
    return groq_client.complete_json(
        prompt,
        system=_CHAT_SYSTEM,
        model=settings.groq_model_fast,
        offline_fallback=fallback,
        use_cache=False,
    )
