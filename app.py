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
import cloudinary
import cloudinary.uploader

# Load environment variables from .env file
load_dotenv()

# Check required environment variables
required_vars = [
    'OPENAI_API_KEY',
    'CLOUDINARY_CLOUD_NAME',
    'CLOUDINARY_API_KEY',
    'CLOUDINARY_API_SECRET'
]

missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing_vars)}")

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Set Tesseract path explicitly
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Set Poppler path explicitly
POPPLER_PATH = os.path.abspath(r'C:\Program Files\poppler\Library\bin')

def save_to_cloud(file_path, public_id):
    try:
        result = cloudinary.uploader.upload(
            file_path,
            public_id=public_id,
            resource_type="auto"
        )
        return result['secure_url']
    except Exception as e:
        print(f"Error uploading to Cloudinary: {str(e)}")
        return None

def process_pdf_with_ocr(pdf_path):
    print(f"Converting PDF: {pdf_path}")
    # Convert PDF to images using explicit Poppler path
    try:
        images = convert_from_path(
            pdf_path,
            poppler_path=POPPLER_PATH
        )
        print(f"Successfully converted {len(images)} pages")
    except Exception as e:
        print(f"Error converting PDF: {str(e)}")
        raise
    
    # Process each page with OCR
    text = ""
    for i, image in enumerate(images):
        print(f"Processing page {i+1}/{len(images)} with OCR")
        text += pytesseract.image_to_string(image, lang='por') + "\n"
    
    return text

def extract_fields_with_openai(text):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Você é um assistente especializado em extrair informações estruturadas de textos de registros imobiliários."},
                {"role": "user", "content": text}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "registro_imovel",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "cidade_do_imovel": {"type": "string", "description": "Nome da cidade onde o imóvel está localizado"},
                            "zona": {"type": "string", "description": "Urbana ou rural"},
                            "tipo_do_imovel": {"type": "string", "description": "Classificação do imóvel (e.g., terreno, casa, apartamento)"},
                            "unidade_de_medida": {"type": "string", "description": "Medida padrão (e.g., metros quadrados)"},
                            "area_total": {"type": "string", "description": "Área total do imóvel"},
                            "area_atual": {"type": "string", "description": "Área atualizada do imóvel"},
                            "area_construida": {"type": "string", "description": "Área construída no terreno (se houver)"},
                            "area_privativa": {"type": "string", "description": "Área de uso exclusivo do imóvel"},
                            "area_comum": {"type": "string", "description": "Área compartilhada, em caso de condomínios"},
                            "fracao_ideal": {"type": "string", "description": "Percentual de propriedade sobre o todo (condomínios ou terrenos compartilhados)"},
                            "inscricao_imobiliaria": {"type": "string", "description": "Número de identificação municipal ou fiscal"},
                            "informacoes_adicionais": {"type": "string", "description": "Campo para descrever algo relevante sobre o imóvel"},
                            "localizacao": {"type": "string", "description": "Rua/número ou endereço cadastrado"},
                            "ato": {"type": "string", "description": "Identificação do tipo de registro (e.g., usucapião)"},
                            "data": {"type": "string", "description": "Data da transação ou registro"},
                            "transacao": {"type": "string", "description": "Valor da transação registrada (se aplicável)"},
                            "avaliacao": {"type": "string", "description": "Valor avaliado do imóvel"},
                            "area_transmitida": {"type": "string", "description": "Área envolvida na transação"},
                            "titulo": {"type": "string", "description": "Descrição do título ou documento relacionado à transação"},
                            "tipo_de_parte": {"type": "string", "description": "Indica se é adquirente, transmitente, etc"},
                            "dependencia": {"type": "string", "description": "Código de dependência relacionado ao proprietário"},
                            "cpf_cnpj": {"type": "string", "description": "Número de identificação do proprietário (pessoa física ou jurídica)"},
                            "nome": {"type": "string", "description": "Nome do proprietário registrado"},
                            "dados_do_conjuge": {"type": "string", "description": "Informações do cônjuge (nome, CPF, qualificação)"},
                            "procurador": {"type": "string", "description": "Informação de procurador, se aplicável"},
                            "participacao": {"type": "string", "description": "Percentual de propriedade individual"},
                            "modelo_de_qualificacao": {"type": "string", "description": "Modelo para categorizar o proprietário"},
                            "logradouro_descricao_livre": {"type": "string", "description": "Nome das ruas que formam o entorno do imóvel"},
                            "distancia_da_esquina": {"type": "string", "description": "Medida de distância das esquinas"},
                            "faz_esquina": {"type": "string", "description": "Indica se a rua faz esquina com outra"},
                            "editor_de_texto": {"type": "string", "description": "Permite adicionar uma descrição detalhada do imóvel"}
                        },
                        "required": [
                            "cidade_do_imovel",
                            "zona",
                            "tipo_do_imovel",
                            "unidade_de_medida",
                            "area_total",
                            "area_atual",
                            "area_construida",
                            "area_privativa",
                            "area_comum",
                            "fracao_ideal",
                            "inscricao_imobiliaria",
                            "informacoes_adicionais",
                            "localizacao",
                            "ato",
                            "data",
                            "transacao",
                            "avaliacao",
                            "area_transmitida",
                            "titulo",
                            "tipo_de_parte",
                            "dependencia",
                            "cpf_cnpj",
                            "nome",
                            "dados_do_conjuge",
                            "procurador",
                            "participacao",
                            "modelo_de_qualificacao",
                            "logradouro_descricao_livre",
                            "distancia_da_esquina",
                            "faz_esquina",
                            "editor_de_texto"
                        ],
                        "additionalProperties": False
                    }
                }
            }
        )
        
        # Get the response content
        content = response.choices[0].message.content.strip()
        print("OpenAI Response:", content)  # Debug print
        
        # Try to parse the JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {str(e)}")
            print(f"Raw content: {content}")
            raise Exception("Failed to parse OpenAI response as JSON. Please try again.") from e
            
    except Exception as e:
        print(f"Error in extract_fields_with_openai: {str(e)}")
        raise Exception(f"Error processing document: {str(e)}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    # Initialize variables that might need cleanup
    pdf_path = None
    text_path = None
    json_path = None
    
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if file:
            # Save the uploaded file temporarily
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = os.path.splitext(filename)[0]
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{base_filename}_{timestamp}.pdf")
            file.save(pdf_path)
            
            try:
                # Process the PDF with OCR
                text = process_pdf_with_ocr(pdf_path)
                print("OCR completed successfully")
                
                # Save files to cloud
                text_filename = f"{base_filename}_{timestamp}_ocr.txt"
                text_path = os.path.join(app.config['UPLOAD_FOLDER'], text_filename)
                with open(text_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                
                # Upload to cloud
                text_url = save_to_cloud(text_path, f"ocr/{text_filename}")
                print(f"Text file uploaded to cloud: {text_url}")
                
                # Extract fields with OpenAI
                try:
                    extracted_data = extract_fields_with_openai(text)
                    print("OpenAI extraction completed")
                except Exception as e:
                    return jsonify({
                        'error': str(e),
                        'text': text,
                        'ocr_text_url': text_url
                    }), 500
                
                # Save JSON
                json_filename = f"{base_filename}_{timestamp}_data.json"
                json_path = os.path.join(app.config['UPLOAD_FOLDER'], json_filename)
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(extracted_data, f, ensure_ascii=False, indent=2)
                
                # Upload JSON to cloud
                json_url = save_to_cloud(json_path, f"json/{json_filename}")
                print(f"JSON file uploaded to cloud: {json_url}")
                
                response_data = {
                    'message': 'File processed successfully',
                    'text': text,
                    'ocr_text_url': text_url,
                    'json_data_url': json_url,
                    'extracted_data': extracted_data
                }
                
                print("Sending response:", response_data)
                return jsonify(response_data)
                
            except Exception as e:
                print(f"Error processing file: {str(e)}")
                import traceback
                traceback.print_exc()
                raise
                
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
        
    finally:
        # Clean up any temporary files that were created
        for path in [pdf_path, text_path, json_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    print(f"Cleaned up temporary file: {path}")
                except Exception as e:
                    print(f"Error cleaning up {path}: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True) 