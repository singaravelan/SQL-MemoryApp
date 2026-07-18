# Exam Quiz

Local Streamlit quiz app for importing text exams, parsing them through a local Ollama model, and saving quiz attempts in SQLite. UTF-8 (including Japanese) is preserved.

## Start

```bash
python3 -m pip install -r requirements.txt
ollama serve
ollama pull llama3.2
streamlit run app.py
```

Set `OLLAMA_MODEL`, `OLLAMA_URL`, `OLLAMA_TIMEOUT_SECONDS` (default 12000), and optionally `EXAM_DB_PATH` in your environment, or edit them in the sidebar. Sidebar changes are stored in `exams.db` and reused at the next launch. Copy `.env.example` as a reference; the sidebar is the built-in configuration path and no dotenv package is required.

## Use

1. In **Ingest Exam**, upload a UTF-8 `.txt` file and select **Parse with Ollama**.
2. Review or correct the returned JSON, then **Validate and save**. Existing filenames require the explicit replacement checkbox.
3. Select **Take Exam**, answer the questions, and submit. Attempts are stored in `exams.db` and visible under **Attempts**.

The parser rejects missing answer keys, fewer than two options, invalid correct options, duplicate section/question pairs, and any model-reported `parsing_issues`. The JSON editor is the retry/edit path for malformed model output.
