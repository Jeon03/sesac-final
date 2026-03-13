import os
import pdfplumber
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

current_file_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))

# 루트에 있는 .env 파일을 명시적으로 로드
env_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path=env_path)

def save_pdf_to_chroma(pdf_path, db_path):
    # 환경 변수에서 API 키 가져오기
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print(f"❌ 에러: API 키를 찾을 수 없습니다. 경로를 확인하세요: {env_path}")
        return

    print(f"✅ API Key 로드 성공 (앞글자): {api_key[:7]}...")


    embeddings = OpenAIEmbeddings(openai_api_key=api_key)

    # PDF에서 텍스트 추출 (pdfplumber 사용)
    documents = []
    print(f"📄 파일 읽기 시작: {pdf_path}")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    # 페이지 번호와 소스 파일명을 메타데이터로 저장
                    documents.append(Document(
                        page_content=text,
                        metadata={"page": page.page_number, "source": os.path.basename(pdf_path)}
                    ))
        print(f"📖 총 {len(documents)} 페이지 추출 완료")
    except Exception as e:
        print(f"❌ PDF 읽기 중 오류 발생: {e}")
        return

    # 텍스트를 의미 있는 단위로 쪼개기 (Chunking)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=100
    )
    chunks = text_splitter.split_documents(documents)
    print(f"✂️ 데이터를 {len(chunks)}개의 조각으로 나누었습니다.")

    # ChromaDB에 저장
    print("🧠 벡터 변환 및 DB 저장 중... 잠시만 기다려주세요.")
    vector_db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=db_path,
        collection_name="k_beauty_hs_guide"
    )
    
    print(f"✨ 'k_beauty_hs_guide' 컬렉션에 {len(chunks)}개 데이터 저장 완료!")
    print(f"📁 저장 위치: {db_path}")
    return vector_db

# --- [실행부] ---
if __name__ == "__main__":
    # PDF 파일 경로: 루트/data/hs-code.pdf
    pdf_file = os.path.join(project_root, "data", "hs-code.pdf")
    
    # DB 저장 경로: 루트/chroma_db
    db_storage = os.path.join(project_root, "chroma_db")

    if os.path.exists(pdf_file):
        save_pdf_to_chroma(pdf_file, db_storage)
    else:
        print(f"❌ 파일을 찾을 수 없습니다: {pdf_file}")