import wikipedia
import os

# Danh sách các công ty/thực thể công nghệ và AI tiêu biểu (Đã bỏ Cohere)
COMPANIES = [
    "OpenAI",
    "Google",
    "Alphabet Inc.",
    "DeepMind",
    "Anthropic",
    "Microsoft",
    "NVIDIA",
    "Meta Platforms",
    "Tesla, Inc.",
    "Amazon (company)",
    "Apple Inc.",
    "Mistral AI",
    "Databricks",
    "Hugging Face",
    "Palantir Technologies",
    "Perplexity AI",
    "Sam Altman",
    "Elon Musk",
    "Demis Hassabis",
    "Dario Amodei",
    "Larry Page",
    "Sergey Brin",
    "Sundar Pichai",
    "Satya Nadella",
    "Jensen Huang",
    "Mark Zuckerberg"
]

def fetch_wikipedia_data(topic_list, output_file):
    """Lấy dữ liệu từ Wikipedia cho danh sách chủ đề và lưu vào file."""
    if os.path.exists(output_file):
        os.remove(output_file)
        
    print(f"🚀 Bắt đầu lấy dữ liệu sạch cho {len(topic_list)} chủ đề...")
    
    with open(output_file, "a", encoding="utf-8") as f:
        for i, topic in enumerate(topic_list):
            try:
                print(f"🔍 [{i+1}/{len(topic_list)}] Đang lấy dữ liệu: {topic}...")
                page = wikipedia.page(topic, auto_suggest=False)
                content = page.content
                truncated_content = content[:10000] 
                
                f.write(f"SOURCE: Wikipedia - {topic}\n")
                f.write(f"TITLE: {page.title}\n")
                f.write(f"CONTENT:\n{truncated_content}\n")
                f.write("\n" + "="*50 + "\n\n")
            except Exception as e:
                print(f"❌ Lỗi khi lấy dữ liệu cho {topic}: {e}")
                
    print(f"✅ Đã hoàn thành! Dữ liệu sạch được lưu tại: {output_file}")

if __name__ == "__main__":
    OUTPUT_FILE = "data/tech_company_corpus.txt"
    os.makedirs("data", exist_ok=True)
    fetch_wikipedia_data(COMPANIES, OUTPUT_FILE)
