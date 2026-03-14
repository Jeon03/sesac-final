import os, json, re
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from market_api.models import MarketStat, HsClassification


def get_hs_code(cat):
    """
    1단계: HsClassification DB에서 기존 판정 결과(코드 + 근거) 조회
    2단계: 없을 경우 RAG를 통해 신규 판정 후 DB 저장
    """

    # --- [1단계: DB 선 매칭] ---
    cached = HsClassification.objects.filter(category=cat).first()
    if cached:
        print(f"[DB] {cat}: 기존 HS 코드({cached.hs_code}) 재사용 (AI 호출 생략)")
        return cached.hs_code, cached.reason

    # MarketStat에만 있고 HsClassification이 없는 기존 데이터 호환 처리
    existing_stat = MarketStat.objects.filter(category=cat).first()

    # --- [2단계: DB에 없을 경우 RAG 실행] ---
    print(f"[AI] {cat}: 새로운 카테고리 - AI 분석 시작...")

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

    # MarketStat에 기존 HS 코드가 있으면 RAG 컨텍스트 기반으로 근거만 생성
    if existing_stat:
        hs_code = existing_stat.hs_code
        # ChromaDB에서 관련 문서 검색
        docs = retriever.invoke(f"'{cat}' HS 코드 {hs_code} 분류 근거")
        context_text = "\n\n".join(doc.page_content for doc in docs)
        reason_prompt = ChatPromptTemplate.from_messages([
            ("system", "화장품 관세사 AI입니다. 아래 [가이드북 문맥]에만 근거해 "
                       "주어진 HS 코드의 분류 근거를 2~3문장으로 설명하세요. "
                       "문맥에 없는 내용은 절대 추가하지 마세요.\n\n[가이드북 문맥]\n{context}"),
            ("human", "카테고리: {category}\nHS 코드: {hs_code}"),
        ])
        reason_chain = reason_prompt | llm
        reason_result = reason_chain.invoke({"context": context_text, "category": cat, "hs_code": hs_code})
        reason = reason_result.content.strip()
    else:
        res = chain.invoke({"input": f"'{cat}' 품목의 HS 코드 판정"})
        try:
            data = json.loads(res["answer"])
            hs_code = re.sub(r'[^0-9]', '', data["hs_code"])
            reason = data["reason"]
            if len(hs_code) != 10:
                return None, "가이드북에서 정확한 코드를 찾을 수 없습니다."
        except Exception:
            return None, "AI 판정 데이터 파싱 실패"

    # 판정 결과 DB 저장
    HsClassification.objects.update_or_create(
        category=cat,
        defaults={"hs_code": hs_code, "reason": reason},
    )
    print(f"[OK] {cat}: HS 코드({hs_code}) 판정 근거 DB 저장 완료")
    return hs_code, reason