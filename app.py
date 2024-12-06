import os
from flask import Flask, request, render_template, send_file, jsonify
from werkzeug.utils import secure_filename
import pytesseract
from pdf2image import convert_from_path
import pandas as pd
from openai import OpenAI
import json
from datetime import datetime
import sys
from dotenv import load_dotenv
import subprocess

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize OpenAI client with API key from environment variable
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY')
)

# Set Tesseract path explicitly
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Set Poppler path explicitly
POPPLER_PATH = os.path.abspath(r'C:\Program Files\poppler\Library\bin')

def verify_poppler_installation():
    required_files = ['pdfinfo.exe', 'pdftoppm.exe']
    missing_files = []
    
    print(f"Checking Poppler in: {POPPLER_PATH}")
    if not os.path.exists(POPPLER_PATH):
        raise RuntimeError(f"Poppler directory not found at: {POPPLER_PATH}")
    
    for file in required_files:
        file_path = os.path.join(POPPLER_PATH, file)
        if not os.path.exists(file_path):
            missing_files.append(file)
    
    if missing_files:
        raise RuntimeError(
            f"Missing Poppler files: {', '.join(missing_files)}\n"
            f"Please ensure Poppler is installed correctly in: {POPPLER_PATH}"
        )
    
    # Add Poppler to PATH temporarily
    os.environ['PATH'] = POPPLER_PATH + os.pathsep + os.environ.get('PATH', '')
    print(f"Added Poppler to PATH: {POPPLER_PATH}")
    
    return True

def process_pdf_with_ocr(pdf_path):
    print(f"Converting PDF: {pdf_path}")
    
    # Verify Poppler installation
    verify_poppler_installation()
    
    # Convert PDF to images using explicit Poppler path
    try:
        images = convert_from_path(
            pdf_path,
            poppler_path=POPPLER_PATH
        )
        print(f"Successfully converted {len(images)} pages")
    except Exception as e:
        print(f"Error converting PDF: {str(e)}")
        print(f"Current PATH: {os.environ.get('PATH')}")
        print(f"Poppler files in directory:")
        try:
            files = os.listdir(POPPLER_PATH)
            for file in files:
                print(f"  - {file}")
        except Exception as dir_error:
            print(f"Error listing directory: {str(dir_error)}")
        raise
    
    # Process each page with OCR
    text = ""
    for i, image in enumerate(images):
        print(f"Processing page {i+1}/{len(images)} with OCR")
        text += pytesseract.image_to_string(image, lang='por') + "\n"
    
    return text

def extract_fields_with_openai(text):
    # Read the fields from Excel file
    fields_df = pd.read_excel('Campos_matricula.xlsx')
    
    # Create a dictionary of fields and their descriptions
    fields_dict = dict(zip(fields_df['Campo'], fields_df['Descrição']))
    
    # Create the JSON format string with field descriptions
    field_examples = []
    for field, desc in fields_dict.items():
        # Clean the field name for JSON
        clean_field = field.replace('/', '_').replace(' ', '_')
        field_examples.append(f'"{clean_field}": "Extrair: {desc}"')
    
    json_format = ',\n        '.join(field_examples)
    
    # Prepare the prompt for OpenAI with structured outputs
    prompt = f"""Extraia os seguintes campos do texto abaixo, usando o formato especificado.
    Se um campo não for encontrado no texto, retorne null ou uma string vazia.

    <output_format>
    {{
        {json_format}
    }}
    </output_format>

    Texto para análise:
    {text}

    Instruções adicionais:
    - Use apenas informações presentes no texto
    - Mantenha os valores exatamente como aparecem no texto
    - Para campos numéricos, mantenha o formato original
    - Se um campo não for encontrado, use null
    - Retorne apenas o JSON, sem explicações adicionais"""
    
    print("Enviando requisição para OpenAI com o prompt:")
    print(prompt)
    
    # Call OpenAI API
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "Você é um assistente especializado em extrair informações estruturadas de textos de registros imobiliários. Retorne apenas o JSON solicitado, sem explicações adicionais."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0
        )
        
        # Print raw response for debugging
        print("\nResposta da OpenAI (raw):")
        print(response)
        
        # Extract JSON from the response
        response_text = response.choices[0].message.content
        if not response_text:
            raise RuntimeError("Resposta vazia da OpenAI")
            
        print("\nTexto da resposta:")
        print(response_text)
        
        # Clean the response text
        response_text = response_text.strip()
        if response_text.startswith('```json'):
            response_text = response_text.split('```json')[1]
        if response_text.endswith('```'):
            response_text = response_text.rsplit('```', 1)[0]
        response_text = response_text.strip()
        
        print("\nTexto limpo da resposta:")
        print(response_text)
        
        # Parse the response to ensure it's valid JSON
        try:
            result = json.loads(response_text)
            print("\nJSON processado:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return result
        except json.JSONDecodeError as e:
            print(f"\nErro ao processar JSON:")
            print(f"Mensagem de erro: {str(e)}")
            print(f"Posição: {e.pos}")
            print(f"Linha: {e.lineno}, Coluna: {e.colno}")
            print(f"Documento: {e.doc}")
            raise RuntimeError(f"Falha ao processar resposta da OpenAI como JSON: {str(e)}")
            
    except Exception as e:
        print(f"\nErro durante a requisição ou processamento:")
        print(f"Tipo do erro: {type(e).__name__}")
        print(f"Mensagem de erro: {str(e)}")
        raise

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        # Save the uploaded file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = os.path.splitext(filename)[0]
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{base_filename}_{timestamp}.pdf")
        file.save(pdf_path)
        
        # Process the PDF with OCR
        text = process_pdf_with_ocr(pdf_path)
        
        # Save the OCR text
        text_filename = f"{base_filename}_{timestamp}_ocr.txt"
        text_path = os.path.join(app.config['UPLOAD_FOLDER'], text_filename)
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        # Extract fields with OpenAI
        extracted_data = extract_fields_with_openai(text)
        
        # Save the extracted data
        json_filename = f"{base_filename}_{timestamp}_data.json"
        json_path = os.path.join(app.config['UPLOAD_FOLDER'], json_filename)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(extracted_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'message': 'File processed successfully',
            'text': text,  # Include the full extracted text
            'ocr_text_file': text_filename,
            'json_data_file': json_filename,
            'extracted_data': extracted_data
        })

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(
        os.path.join(app.config['UPLOAD_FOLDER'], filename),
        as_attachment=True
    )

if __name__ == '__main__':
    app.run(debug=True) 