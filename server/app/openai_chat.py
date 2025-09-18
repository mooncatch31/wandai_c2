from app.settings import settings

def answer_with_openai(standalone: str, context_block: str, key: str | None) -> dict | None:
    api_key = key or settings.openai_api_key
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        system = (
            "Answer strictly using the provided Context. If the Context lacks information, "
            "explain what is missing. Return JSON with keys: answer, confidence (high|medium|low), "
            "missing_info [strings], suggested_enrichment [strings]."
        )
        user = f"Question:\n{standalone}\n\nContext:\n{context_block}\n"
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        import json
        return json.loads(resp.choices[0].message.content)
    except Exception:
        return None
