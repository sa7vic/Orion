"""
Generate pillar -- unstructured side. Uses Groq to script the human-facing
content of an attack (call transcripts, KYC field mismatches, QR/app
metadata) conditioned on a taxonomy entry, so the Generate module actually
produces content the Defend specialists can be evaluated against.
"""
from app.groq_client import groq_client
from app.config import settings

_TRANSCRIPT_SYSTEM = (
    "You write short realistic FICTIONAL call-transcript excerpts for a "
    "fraud-detection training simulator. These are used ONLY to train and "
    "test a defensive classifier -- never sent to a real person. Keep it "
    "to 4-6 lines of dialogue."
)


def generate_vishing_transcript(persona: str = "fake bank support agent") -> dict:
    prompt = (
        f"Write a short fictional phone-call transcript excerpt where a "
        f"scammer poses as a {persona} and tries to obtain an OTP or UPI "
        f"PIN from the victim, using urgency and authority. Label each line "
        f'Speaker A (scammer) / Speaker B (victim). Return JSON: '
        f'{{"transcript": "...", "scam_markers_used": ["...","..."]}}'
    )
    fallback = {
        "transcript": (
            "Speaker A: Sir, this is urgent, your account will be blocked in 2 minutes "
            "unless you verify the OTP just sent to you.\n"
            "Speaker B: Which OTP, I didn't request anything.\n"
            "Speaker A: This is standard bank security, please read it out now or your "
            "funds will be frozen."
        ),
        "scam_markers_used": ["urgency", "authority_impersonation", "otp_request"],
    }
    return groq_client.complete_json(
        prompt, system=_TRANSCRIPT_SYSTEM, model=settings.groq_model_fast, offline_fallback=fallback
    )


_KYC_SYSTEM = (
    "You generate FICTIONAL synthetic-identity test fixtures for a fraud "
    "detection training simulator: pairs of (application_form_fields, "
    "submitted_document_fields) with a deliberate inconsistency of the kind "
    "seen in synthetic-identity fraud. Never use real people's data."
)


def generate_kyc_mismatch_case() -> dict:
    prompt = (
        "Generate a fictional KYC case with a subtle field inconsistency "
        "between the application form and the submitted ID document (e.g. "
        "DOB mismatch, address mismatch, name spelling variant reused "
        "across multiple applications). Return JSON: "
        '{"application_fields": {...}, "document_fields": {...}, '
        '"inconsistency_type": "..."}'
    )
    fallback = {
        "application_fields": {"name": "Rohan Mehta", "dob": "1994-03-11", "address": "Pune, MH"},
        "document_fields": {"name": "Rohan Mehta", "dob": "1991-03-11", "address": "Pune, MH"},
        "inconsistency_type": "dob_mismatch",
    }
    return groq_client.complete_json(
        prompt, system=_KYC_SYSTEM, model=settings.groq_model_fast, offline_fallback=fallback
    )


_CHAT_SYSTEM = (
    "You write a short FICTIONAL adaptive scam chat script for a fraud "
    "training simulator, showing how the scam persuasion escalates over "
    "3-4 turns based on victim hesitation. Never target a real person."
)


def generate_adaptive_chat_snippet() -> dict:
    prompt = (
        "Write a 3-4 turn fictional chat exchange where a scam bot "
        "escalates persuasion tactics (trust-building -> urgency -> "
        "authority) as the 'victim' expresses doubt. Return JSON: "
        '{"chat": "...", "escalation_stages": ["...","..."]}'
    )
    fallback = {
        "chat": "Bot: Congratulations, you're eligible for a refund.\n"
                "User: I didn't request a refund.\n"
                "Bot: It's already been processed, we just need to verify your UPI ID "
                "before the deadline expires in 10 minutes.",
        "escalation_stages": ["trust_building", "urgency"],
    }
    return groq_client.complete_json(
        prompt, system=_CHAT_SYSTEM, model=settings.groq_model_fast, offline_fallback=fallback
    )
