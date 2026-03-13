import os, json, re
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from market_api.models import MarketStat 

def get_hs_code(cat):
    """
    1단계: DB에서 기존 매칭 내역 검색 (선 매칭)
    2단계: 없을 경우 RAG를 통해 신규 판정
    """
    
    # --- [1단계: DB 선 매칭] ---
    # 이미 분석된 적이 있는 카테고리라면 DB에 통계 데이터가 있으므로 HS 코드를 바로 추출합니다.
    existing_entry = MarketStat.objects.filter(category=cat).first()
    
    if existing_entry:
        print(f"📦 {cat}: DB에서 기존 HS 코드({existing_entry.hs_code})를 찾았습니다. (AI 호출 생략)")
        return existing_entry.hs_code, "DB 내 기존 분석 데이터를 재사용합니다."

    # --- [2단계: DB에 없을 경우 RAG 실행] ---
    print(f"🤖 {cat}: 새로운 카테고리입니다. AI 분석을 시작합니다...")
    
    db_path = os.path.join(os.getcwd(), "chroma_db")
    embeddings = OpenAIEmbeddings()
    vector_db = Chroma(persist_directory=db_path, embedding_function=embeddings, collection_name="k_beauty_hs_guide")
    retriever = vector_db.as_retriever(search_kwargs={"k": 3})
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "화장품 관세사 AI입니다. [문맥]에만 근거해 10자리 HS 코드를 판정하세요. "
                   "정보가 없다면 'NONE'을, 있다면 반드시 JSON만 반환하세요: "
                   "{{\"hs_code\": \"...\", \"reason\": \"...\"}}"),
        ("system", "[문맥]\n{context}"),
        ("human", "{input}"),
    ])

    chain = create_retrieval_chain(retriever, create_stuff_documents_chain(llm, prompt))
    res = chain.invoke({"input": f"'{cat}' 품목의 HS 코드 판정"})
    
    try:
        data = json.loads(res["answer"])
        code = re.sub(r'[^0-9]', '', data["hs_code"])
        
        if len(code) == 10:
            return code, data["reason"]
        return None, "가이드북에서 정확한 코드를 찾을 수 없습니다."
    except:
        return None, "AI 판정 데이터 파싱 실패"