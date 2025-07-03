import os
from flask import Flask, render_template, request, send_file
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm
from datetime import datetime
from dotenv import load_dotenv
import openai

load_dotenv()

# Set up OpenAI key from .env
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('generated_reports', exist_ok=True)

# 🔁 GPT-based Description Generator
def generate_description(prompt_text):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an assistant generating formal NSS activity reports."},
                {"role": "user", "content": f"Write a formal report description for the following points:\n{prompt_text}"}
            ],
            temperature=0.7,
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating description: {str(e)}"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        data = request.form
        files = request.files.getlist('photos')
        image_paths = []

        for i, f in enumerate(files):
            if f and f.filename:
                path = os.path.join(app.config['UPLOAD_FOLDER'], f"photo_{i}.jpg")
                f.save(path)
                image_paths.append(path)

        # ✅ New: check if user selected AI or Manual
        desc_type = data.get('desc_type', 'manual')

        if desc_type == 'ai' and os.getenv("OPENAI_API_KEY"):
            description = generate_description(data['notes'])  # use GPT
        else:
            description = data['notes']  # use user-typed content

        doc = DocxTemplate("templates/report_template.docx")

        image_context = {}
        for i in range(4):
            key = f'image{i+1}'
            if i < len(image_paths):
                image_context[key] = InlineImage(doc, image_paths[i], width=Mm(60))
            else:
                image_context[key] = ''

        context = {
            'category': data['category'],
            'program': data['program'],
            'date': datetime.strptime(data['date'], "%Y-%m-%d").strftime("%d %B %Y"),
            'duration': data['duration'],
            'description': description,
            **image_context
        }

        filename = f"report_{datetime.now().strftime('%Y%m%d%H%M%S')}.docx"
        filepath = os.path.join("generated_reports", filename)
        doc.render(context)
        doc.save(filepath)

        return send_file(filepath, as_attachment=True)

    return render_template('form.html')

if __name__ == '__main__':
    app.run(debug=True)
