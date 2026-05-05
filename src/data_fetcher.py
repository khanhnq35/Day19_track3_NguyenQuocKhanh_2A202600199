import time
import wikipedia
import os

# Danh sách các công ty/thực thể công nghệ và AI tiêu biểu 
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

MAX_RETRIES = 3
DELAY_BETWEEN_CALLS = 3  # seconds between each API call


def fetch_wikipedia_data(topic_list, output_file):
    """Lấy dữ liệu từ Wikipedia cho danh sách chủ đề và lưu vào file."""
    if os.path.exists(output_file):
        os.remove(output_file)

    print(f"🚀 Bắt đầu lấy dữ liệu sạch cho {len(topic_list)} chủ đề...")

    success_count = 0
    with open(output_file, "a", encoding="utf-8") as f:
        for i, topic in enumerate(topic_list):
            page_content = None
            page_title = None
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    print(f"🔍 [{i+1}/{len(topic_list)}] Đang lấy dữ liệu: {topic} (attempt {attempt})...")
                    page = wikipedia.page(topic, auto_suggest=False)
                    page_content = page.content[:10000]
                    page_title = page.title
                    break
                except Exception as e:
                    print(f"   ⚠️ Attempt {attempt} failed: {e}")
                    if attempt < MAX_RETRIES:
                        wait = attempt * 2
                        print(f"   ⏳ Chờ {wait}s trước khi thử lại...")
                        time.sleep(wait)
                    else:
                        print(f"   ❌ Bỏ qua {topic} sau {MAX_RETRIES} lần thử.")

            if page_content:
                f.write(f"SOURCE: Wikipedia - {topic}\n")
                f.write(f"TITLE: {page_title}\n")
                f.write(f"CONTENT:\n{page_content}\n")
                f.write("\n" + "=" * 50 + "\n\n")
                success_count += 1

            # Delay giữa các lần gọi để tránh rate limit
            if i < len(topic_list) - 1:
                time.sleep(DELAY_BETWEEN_CALLS)

    print(f"✅ Hoàn thành! {success_count}/{len(topic_list)} chủ đề thành công.")
    print(f"📄 Dữ liệu lưu tại: {output_file}")


if __name__ == "__main__":
    OUTPUT_FILE = "data/tech_company_corpus.txt"
    os.makedirs("data", exist_ok=True)
    fetch_wikipedia_data(COMPANIES, OUTPUT_FILE)
