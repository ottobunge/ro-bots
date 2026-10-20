"""Text-only policy for pinned MAIN/pre-re 20180704 native public chat.

The unchanged wire adds one NUL; clif_process_message adds another byte in its
post-20151001 branch and rejects messageLength > CHAT_SIZE_MAX - 1 (255).
Text must also fit clif_GlobalMessage's 255 visible bytes including the selected
sender name and ' : ' separator. Clip one message, never change packet encoding.
"""

PUBLIC_CHAT_TEXT_MAX_BYTES = 253


def public_chat_text(text: str, sender_name: str) -> str:
    """Preserve valid text; clip to both incoming and full peer-message budgets."""
    encoded = text.encode("utf-8")
    budget = min(PUBLIC_CHAT_TEXT_MAX_BYTES, 255 - len(f"{sender_name} : ".encode()))
    if budget < 0:
        message = "sender exceeds public chat budget"
        raise ValueError(message)
    if len(encoded) <= budget:
        return text
    prefix = encoded[:budget]
    try:
        return prefix.decode("utf-8")
    except UnicodeDecodeError as error:
        # Strict encoding proved validity; only the final code point can be cut.
        return prefix[: error.start].decode("utf-8")
