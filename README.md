# Cartório AI - Extrator de Documentos

Uma aplicação web para extrair e estruturar dados de documentos PDF de cartório usando OCR e IA.

## Requisitos

1. Python 3.9+
2. Tesseract OCR
3. Poppler (para PDF2Image)
4. Chave de API do OpenAI

## Instalação

1. Instale o Tesseract OCR:
   - Windows:
     1. Baixe o instalador de https://github.com/UB-Mannheim/tesseract/wiki
     2. Execute o instalador e **IMPORTANTE**: 
        - Instale em `C:\Program Files\Tesseract-OCR`
        - Na tela de seleção de idiomas, selecione "Portuguese"
     3. Adicione ao PATH do sistema:
        - Abra "Editar as variáveis de ambiente do sistema"
        - Clique em "Variáveis de Ambiente"
        - Em "Variáveis do Sistema", encontre e selecione "Path"
        - Clique em "Editar" e depois em "Novo"
        - Adicione `C:\Program Files\Tesseract-OCR`
        - Clique "OK" em todas as janelas
     4. Verifique a instalação:
        - Abra um novo PowerShell
        - Execute: `tesseract --version`
        - Se aparecer a versão, a instalação está correta

2. Instale o Poppler:
   - Windows:
     1. Baixe o arquivo zip mais recente de: https://github.com/oschwartz10612/poppler-windows/releases/
     2. Extraia o arquivo zip para `C:\Program Files\poppler`
     3. O diretório `bin` deve estar em `C:\Program Files\poppler\Library\bin`
     4. Não é necessário adicionar ao PATH (o programa usa o caminho direto)

3. Instale as dependências Python:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure a chave da API OpenAI:
   1. Crie um arquivo `.env` na raiz do projeto
   2. Adicione sua chave de API no formato:
      ```
      OPENAI_API_KEY=sua-chave-api-aqui
      ```
   3. Salve o arquivo

## Uso

1. Execute o aplicativo:
   ```bash
   python app.py
   ```

2. Abra o navegador em `http://localhost:5000`

3. Faça upload de um arquivo PDF ou arraste e solte na área indicada

4. O sistema irá:
   - Extrair o texto do PDF usando OCR
   - Processar o texto usando IA para extrair campos estruturados
   - Disponibilizar o download do texto extraído e dos dados estruturados

## Estrutura de Arquivos

- `app.py`: Aplicação principal Flask
- `templates/index.html`: Interface do usuário
- `uploads/`: Diretório onde os arquivos processados são salvos
- `Campos_matricula.xlsx`: Arquivo com a definição dos campos a serem extraídos
- `.env`: Arquivo com a chave da API OpenAI (não versionado)

## Notas

- O OCR está configurado para processar textos em português
- O tamanho máximo de arquivo é 16MB
- Os arquivos processados são salvos com timestamp para evitar conflitos

## Troubleshooting

Se você encontrar o erro "tesseract is not installed or it's not in your PATH":
1. Verifique se o Tesseract está instalado em `C:\Program Files\Tesseract-OCR`
2. Verifique se o executável `tesseract.exe` existe nesse diretório

Se você encontrar o erro relacionado ao Poppler:
1. Verifique se o Poppler está instalado corretamente em `C:\Program Files\poppler`
2. Verifique se os arquivos necessários existem em `C:\Program Files\poppler\Library\bin`
3. Verifique se os arquivos `pdfinfo.exe` e `pdftoppm.exe` estão presentes no diretório bin

Se você encontrar erro de autenticação da OpenAI:
1. Verifique se o arquivo `.env` existe na raiz do projeto
2. Verifique se a chave API está correta no arquivo `.env`
3. Certifique-se de que não há espaços ou caracteres extras na chave