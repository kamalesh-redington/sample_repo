from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from main import run_pipeline

app = FastAPI(title="RAG Chat UI")

query_engine = None

class QueryRequest(BaseModel):
    question: str


def get_query_engine():
    global query_engine
    if query_engine is None:
        index = run_pipeline()
        query_engine = index.as_query_engine()
    return query_engine

@app.get("/", response_class=HTMLResponse)
def root():
    return """<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
    <title>RAG Document Chat</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f4f7fb;
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .chat-window {
            width: min(760px, 100%);
            background: #fff;
            border-radius: 14px;
            box-shadow: 0 18px 45px rgba(15, 23, 42, 0.12);
            overflow: hidden;
        }
        .header {
            background: #1f2937;
            color: #fff;
            padding: 18px 22px;
            font-size: 1.2rem;
            font-weight: 700;
        }
        .messages {
            min-height: 360px;
            max-height: 520px;
            overflow-y: auto;
            padding: 20px;
            background: #f9fafb;
        }
        .message {
            margin-bottom: 18px;
            display: flex;
        }
        .message.user { justify-content: flex-end; }
        .message.bot { justify-content: flex-start; }
        .bubble {
            max-width: 78%;
            padding: 14px 16px;
            border-radius: 16px;
            line-height: 1.5;
            white-space: pre-wrap;
        }
        .bubble.user {
            background: #2563eb;
            color: #fff;
            border-bottom-right-radius: 6px;
        }
        .bubble.bot {
            background: #e5e7eb;
            color: #111827;
            border-bottom-left-radius: 6px;
        }
        .input-area {
            display: flex;
            gap: 12px;
            padding: 18px 22px 22px;
            background: #fff;
        }
        textarea {
            flex: 1;
            resize: vertical;
            min-height: 80px;
            padding: 14px 16px;
            border: 1px solid #d1d5db;
            border-radius: 12px;
            font-size: 1rem;
        }
        button {
            background: #2563eb;
            border: none;
            color: #fff;
            padding: 0 24px;
            border-radius: 12px;
            cursor: pointer;
            font-size: 1rem;
        }
        button:disabled {
            background: #93c5fd;
            cursor: default;
        }
    </style>
</head>
<body>
    <div class=\"chat-window\">
        <div class=\"header\">RAG Document Chat</div>
        <div id=\"messages\" class=\"messages\"></div>
        <form id=\"chat-form\" class=\"input-area\">
            <textarea id=\"question\" placeholder=\"Ask a question about the documents...\"></textarea>
            <button type=\"submit\">Send</button>
        </form>
    </div>
    <script>
        const messages = document.getElementById('messages');
        const form = document.getElementById('chat-form');
        const questionInput = document.getElementById('question');

        function addMessage(text, role) {
            const wrapper = document.createElement('div');
            wrapper.className = `message ${role}`;
            const bubble = document.createElement('div');
            bubble.className = `bubble ${role}`;
            bubble.textContent = text;
            wrapper.appendChild(bubble);
            messages.appendChild(wrapper);
            messages.scrollTop = messages.scrollHeight;
        }

        async function sendQuestion(question) {
            const response = await fetch('/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Unknown error');
            }

            return response.json();
        }

        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const question = questionInput.value.trim();
            if (!question) {
                return;
            }

            addMessage(question, 'user');
            questionInput.value = '';
            const button = form.querySelector('button');
            button.disabled = true;
            button.textContent = 'Thinking...';

            try {
                const data = await sendQuestion(question);
                addMessage(data.answer, 'bot');
            } catch (error) {
                addMessage(`Error: ${error.message}`, 'bot');
            } finally {
                button.disabled = false;
                button.textContent = 'Send';
            }
        });
    </script>
</body>
</html>"""

@app.post("/query")
def query_document(request: QueryRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question may not be empty.")

    engine = get_query_engine()

    try:
        response = engine.query(question)
        answer = str(response)
        return {"question": question, "answer": answer}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}")
