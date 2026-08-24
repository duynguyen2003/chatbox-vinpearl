const STREAM_STATUS_LABELS = {
  en: {
    analyzing: 'Understanding your request…',
    understanding: 'Reading the conversation context…',
    planning: 'Preparing the information search…',
    searching: 'Searching for relevant Vinpearl information…',
    evaluating: 'Reviewing the retrieved information…',
    composing: 'Drafting the answer…',
    verifying: 'Checking the answer for accuracy…',
    generating: 'Sending the answer…',
  },
  vi: {
    analyzing: 'Đang phân tích yêu cầu…',
    understanding: 'Đang hiểu ngữ cảnh hội thoại…',
    planning: 'Đang xác định nội dung cần tìm…',
    searching: 'Đang tìm thông tin Vinpearl phù hợp…',
    evaluating: 'Đang đánh giá dữ liệu tìm được…',
    composing: 'Đang soạn câu trả lời…',
    verifying: 'Đang kiểm tra độ chính xác…',
    generating: 'Đang gửi câu trả lời…',
  },
  ko: {
    analyzing: '요청을 분석하고 있습니다…',
    understanding: '대화 맥락을 파악하고 있습니다…',
    planning: '정보 검색 계획을 준비하고 있습니다…',
    searching: '관련 Vinpearl 정보를 찾고 있습니다…',
    evaluating: '검색 결과를 검토하고 있습니다…',
    composing: '답변 초안을 작성하고 있습니다…',
    verifying: '답변의 정확성을 확인하고 있습니다…',
    generating: '답변을 전송하고 있습니다…',
  },
  ja: {
    analyzing: 'リクエストを分析しています…',
    understanding: '会話の文脈を確認しています…',
    planning: '情報検索の準備をしています…',
    searching: '関連するVinpearl情報を検索しています…',
    evaluating: '検索結果を確認しています…',
    composing: '回答を作成しています…',
    verifying: '回答の正確性を確認しています…',
    generating: '回答を送信しています…',
  },
  zh: {
    analyzing: '正在分析您的请求…',
    understanding: '正在理解对话上下文…',
    planning: '正在制定信息检索计划…',
    searching: '正在查找相关的 Vinpearl 信息…',
    evaluating: '正在评估检索结果…',
    composing: '正在组织回答…',
    verifying: '正在核对回答准确性…',
    generating: '正在发送回答…',
  },
}

export function streamStatusLabel(language, stage) {
  const languageLabels = STREAM_STATUS_LABELS[language] || STREAM_STATUS_LABELS.en
  return languageLabels[stage]
    || STREAM_STATUS_LABELS.en[stage]
    || languageLabels.analyzing
}
