# src/ranker.py
import tldextract
from duckduckgo_search import DDGS
from typing import List, Dict

class UniversalRanker:
    def __init__(self):
        # 通用版：通常 .org, .net, .com 都是中性的
        # 如果你特别讨厌社交媒体，可以保留黑名单
        self.BLOCK_DOMAINS = {
            'pinterest', 'facebook', 'twitter', 'instagram', 'tiktok'
        }
        
        # 通用版不需要特定的加分词，或者你可以根据需要动态传入
        # 这里留空，完全依赖搜索引擎的排名
        self.TRUSTED_KEYWORDS = [] 

    def calculate_score(self, result: Dict) -> int:
        score = 50 # 基础分
        url = result.get('href', '')
        
        extracted = tldextract.extract(url)
        domain = extracted.domain.lower()
        
        # 黑名单一票否决
        if domain in self.BLOCK_DOMAINS:
            return -1000

        # 通用逻辑：我们假设排在搜索结果前面的就是好的，不需要太多额外干预
        # 你可以在这里加自己的逻辑，比如：如果是 .edu 还是加点分
        if extracted.suffix == 'edu':
            score += 20
            
        return score

    def search_and_rank(self, query: str, max_results: int = 10) -> List[Dict]:
        # --- 修改点：直接用用户的 query，不要强制加 "pathology" ---
        print(f"🔍 通用搜索: {query} ...")
        
        results = []
        try:
            with DDGS() as ddgs:
                # 搜索图片相关的内容
                raw_results = list(ddgs.text(query, max_results=max_results))
                
                for r in raw_results:
                    score = self.calculate_score(r)
                    if score > 0:
                        r['score'] = score
                        results.append(r)
        except Exception as e:
            print(f"搜索出错: {e}")
            return []

        return sorted(results, key=lambda x: x['score'], reverse=True)