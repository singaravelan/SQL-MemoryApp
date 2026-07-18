# Exam Quiz

Local Streamlit quiz app for importing text exams, parsing them through local Ollama via LangChain schema-guided output, and saving quiz attempts in SQLite. UTF-8 (including Japanese) is preserved.

## Start

```bash
python3 -m pip install -r requirements.txt
ollama serve
ollama pull llama3.2
streamlit run app.py
```

Set `OLLAMA_MODEL`, `OLLAMA_URL`, `OLLAMA_TIMEOUT_SECONDS` (default 12000), and optionally `EXAM_DB_PATH` in your environment, or edit them in the sidebar. Sidebar changes are stored in `exams.db` and reused at the next launch. Copy `.env.example` as a reference; the sidebar is the built-in configuration path and no dotenv package is required.

## Use

1. In **Ingest Exam**, upload a UTF-8 `.txt` file and select **Parse and save with AI**.
2. The app runs schema-guided extraction and one automatic AI repair pass, then saves only a complete exam. Existing filenames require the explicit replacement checkbox.
3. Select **Take Exam**, answer the questions, and submit. Attempts are stored in `exams.db` and visible under **Attempts**.

The parser rejects missing answer keys, fewer than two options, invalid correct options, duplicate section/question pairs, and unresolved model issues. It never asks you to edit generated JSON; retry the AI import if it cannot safely produce a complete exam.
