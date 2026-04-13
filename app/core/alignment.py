import difflib
import re
import jieba
from collections import Counter
from pypinyin import lazy_pinyin

class AlignmentModule:
    def __init__(self):
        # 动态噪音集合
        self.dynamic_noise_set = set()

    def parse_timestamp(self, time_str):
        try:
            parts = time_str.strip().split(':')
            if len(parts) == 3:
                h, m, s = map(int, parts)
                return h * 3600 + m * 60 + s
            return 0
        except:
            return 0

    def format_timestamp(self, seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return "{:02d}:{:02d}:{:02d}".format(int(h), int(m), int(s))

    def analyze_noise(self, ocr_texts, asr_texts):
        """
        核心算法：基于频率差分的噪音发现
        """
        # 1. 对 OCR 和 ASR 全文进行分词
        ocr_tokens = []
        for line in ocr_texts:
            # 过滤掉标点和特殊符号，只保留中英文数字
            clean_line = re.sub(r'[^\w\u4e00-\u9fff]', '', line)
            ocr_tokens.extend(jieba.lcut(clean_line))
            
        asr_tokens = []
        for line in asr_texts:
            clean_line = re.sub(r'[^\w\u4e00-\u9fff]', '', line)
            asr_tokens.extend(jieba.lcut(clean_line))

        # 2. 统计词频
        ocr_counter = Counter(ocr_tokens)
        asr_counter = Counter(asr_tokens)
        
        total_ocr_lines = len(ocr_texts) if ocr_texts else 1
        
        noise_candidates = set()
        
        # 3. 差分分析
        for word, count in ocr_counter.items():
            # A. 频率阈值：如果一个词出现在超过 15% 的 OCR 行中 (水印通常很高频)
            ocr_freq_ratio = count / total_ocr_lines
            
            # B. 长度阈值：忽略单字 (避免误杀 "的", "了")，除非它出现频率极高 (>50%)
            if len(word) < 2 and ocr_freq_ratio < 0.5:
                continue
                
            # C. 跨模态验证：如果 ASR 里几乎没出现过这个词
            # (ASR 出现次数 / OCR 出现次数) < 0.1
            asr_count = asr_counter.get(word, 0)
            
            if ocr_freq_ratio > 0.15 and (asr_count / count) < 0.1:
                noise_candidates.add(word)
                print(f"🗑️ 自动发现噪音模式: '{word}' (OCR频次:{count} | ASR频次:{asr_count})")
        
        self.dynamic_noise_set = noise_candidates

    def clean_text_dynamic(self, text):
        """应用动态发现的噪音库进行清洗"""
        if not text: return ""
        cleaned = text
        for noise in self.dynamic_noise_set:
            cleaned = cleaned.replace(noise, "")
        return cleaned.strip()

    def get_pinyin_similarity(self, text1, text2):
        py1 = "".join(lazy_pinyin(text1))
        py2 = "".join(lazy_pinyin(text2))
        return difflib.SequenceMatcher(None, py1, py2).ratio()

    def align(self, ocr_raw_text, asr_results):
        if not asr_results:
            return ocr_raw_text

        # --- 阶段一：预处理与噪音学习 ---
        
        # 1. 提取纯文本列表用于训练噪音模型
        ocr_lines_struct = []
        raw_ocr_texts = []
        
        lines = [line for line in ocr_raw_text.split('\n') if line.strip()]
        for line in lines:
            try:
                if line.startswith('[') and ']' in line:
                    right_bracket_idx = line.find(']')
                    ts_str = line[1:right_bracket_idx]
                    raw_text = line[right_bracket_idx+1:].strip()
                    
                    if raw_text:
                        ocr_lines_struct.append({
                            'time': self.parse_timestamp(ts_str),
                            'raw_text': raw_text
                        })
                        raw_ocr_texts.append(raw_text)
            except: continue

        asr_texts_list = [seg['text'] for seg in asr_results]
        
        # 2. 运行噪音分析算法
        self.analyze_noise(raw_ocr_texts, asr_texts_list)
        
        # 3. 清洗 OCR 数据
        ocr_data = []
        for item in ocr_lines_struct:
            clean_txt = self.clean_text_dynamic(item['raw_text'])
            if clean_txt: # 如果洗完还有剩
                item['text'] = clean_txt
                ocr_data.append(item)

        # --- 阶段二：对齐合并 (保持之前的逻辑) ---
        merged_subtitles = []

        for asr_seg in asr_results:
            asr_start = asr_seg['start']
            asr_end = asr_seg['end']
            asr_text = asr_seg['text']
            
            final_text = asr_text
            
            matched_candidates = []
            for ocr_item in ocr_data:
                if (asr_start - 2.0) <= ocr_item['time'] <= (asr_end + 2.0):
                    matched_candidates.append(ocr_item)
            
            if matched_candidates:
                best_score = 0
                best_ocr_text = ""
                
                for cand in matched_candidates:
                    ocr_txt = cand['text']
                    char_ratio = difflib.SequenceMatcher(None, asr_text, ocr_txt).ratio()
                    pinyin_ratio = self.get_pinyin_similarity(asr_text, ocr_txt)
                    final_score = max(char_ratio, pinyin_ratio)
                    
                    if final_score > best_score:
                        best_score = final_score
                        best_ocr_text = ocr_txt
                
                if best_score > 0.6:
                    # 标点迁移逻辑
                    if asr_text and asr_text[-1] in ",.?!，。？！" and best_ocr_text[-1] not in ",.?!，。？！":
                        final_text = best_ocr_text + asr_text[-1]
                    else:
                        final_text = best_ocr_text

            merged_subtitles.append(f"[{self.format_timestamp(asr_start)} --> {self.format_timestamp(asr_end)}] {final_text}")

        return "\n".join(merged_subtitles)
