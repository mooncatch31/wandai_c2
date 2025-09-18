import hashlib

def rough_token_count(s: str) -> int:
    # best-effort token estimate
    return max(1, int(len(s) / 4))

def chunk_text(text: str, size_tokens: int, overlap_tokens: int):
    if not text:
        return []
    words = text.split()
    approx_tokens_per_word = 1  # simplifying assumption
    size_words = size_tokens // approx_tokens_per_word
    overlap_words = overlap_tokens // approx_tokens_per_word

    chunks = []
    i = 0
    idx = 0
    while i < len(words):
        end = min(len(words), i + size_words)
        piece = " ".join(words[i:end])
        chunk_sha = hashlib.sha256(piece.encode("utf-8")).hexdigest()
        chunks.append(
            {"idx": idx, "text": piece, "token_count": rough_token_count(piece), "sha": chunk_sha}
        )
        idx += 1
        if end == len(words):
            break
        i = max(i + size_words - overlap_words, end)
    return chunks
