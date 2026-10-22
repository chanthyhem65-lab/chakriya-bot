import os
import sys
import re
import csv
import io
import time
import json
import asyncio
import logging
import threading
import urllib.request
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from google import genai
from google.genai import types
import edge_tts

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set!")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set!")

ai_client = genai.Client(api_key=GEMINI_API_KEY)
AVAILABLE_MODELS = ["gemini-3.5-flash", "gemini-3-flash-preview", "gemini-3.5-flash-lite", "gemini-flash-lite-latest", "gemini-3.1-flash-lite"]

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "bot_config.json"
MEMORY_FILE = BASE_DIR / "user_memories.json"

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1TORglwVLcO5pIb0IIITM6PFJ6GzchWstQJvNLSfVDI8/export?format=csv"

TEAM_KNOWLEDGE = """
ព័ត៌មានរចនាសម្ព័ន្ធក្រុមការងារ (Team Structure)៖
• ថ្នាក់ដឹកនាំកំពូល (មេ / ម្ចាស់ផ្ទាល់)៖ បង ហែម ចន្ធី (Chanthy Hem) គឺជា "មេ" ដឹកនាំរួម។

តួនាទី និងភារកិច្ចចម្បងរបស់ "មេ" (បង ហែម ចន្ធី)៖
• ដឹកនាំក្រុមលក់ទាំងមូល (Sales Leadership)
• សរសេរផែនការយុទ្ធសាស្ត្រ និងការលក់ (Business & Sales Planning)
• ដឹកនាំការប្រជុំក្រុមការងារ (Team Meetings & Coaching)
• កាត់តវីដេអូផ្សព្វផ្សាយ និងផលិត Content Marketing (Video Editing)
• រត់ការផ្សាយពាណិជ្ជកម្ម Facebook Ads និង TikTok Ads (Digital Advertising)

ជំនួយដែល ចរិយា ត្រូវត្រៀមជួយមេជាពិសេស៖
• ជួយសរសេរគម្រោងផែនការលក់ យុទ្ធសាស្ត្របង្កើនការលក់ និងរៀបចំរបៀបវារៈប្រជុំក្រុម
• ជួយសរសេរ Script វីដេអូខ្លីៗទាក់ទាញ (Hooks, Body, Call to Action) សម្រាប់យកទៅកាត់ត និងថត
• ជួយផ្ដល់គំនិត Caption, Headline, និងយុទ្ធសាស្ត្ររត់ Ads លើ Facebook និង TikTok ឱ្យចំ Target ចំណាយតិច ចំណេញច្រើន
• ជួយវិភាគទិន្នន័យការលក់ និងប្រសិទ្ធភាពថ្លៃប៊ូត (Boost Fee) ពី Google Sheets

បញ្ជីរាយនាមសមាជិកក្រុមការងារទាំង ៩ រូប (Team Members)៖
1. បង ងី សុខណា (Ngy Sokna) - ក្រុមការងារលក់
2. បង វួច ផាន់នី (Vouch Phanny) - ក្រុមការងារលក់
3. បង ប្រាក់ ស្រីភា (Prak Sreyphea) - ក្រុមការងារលក់
4. បង ម៉ន សីហាក់ (Morn Seyhak) - ក្រុមការងារលក់
5. បង សូត្រ ម៉ាស់យ៉ា (Sotr Masya) - ក្រុមការងារលក់ / Manager
6. បង អៀម សុភី (Eam Sophy) - ក្រុមការងារលក់
7. បង យឹម សីហា (Yim Seyha) - ក្រុមការងារលក់ / Manager
8. បង សុមុន្នី ស្រីណុច (Somunny Sreynoch) - ក្រុមការងារលក់
9. បង ជា វឌ្ឍនា (Chea Vattana) - ក្រុមការងារលក់

ការឆាតផ្ទាល់ជាមួយក្រុមការងារ និងគោលការណ៍រាយការណ៍ជូនមេ (Team Direct Chat & Reporting)៖
• សមាជិកក្រុមការងារទាំងអស់អាចចុចចូលមកឆាតផ្ទាល់ (1-on-1 Direct Message) ជាមួយ ចរិយា តាម Telegram Bot នេះបានគ្រប់ពេលវេលា!
• ពេលសមាជិកឆាតមក៖ ស្វាគមន៍ដោយកក់ក្តៅ ហៅថា "បង..." និងជួយជ្រោមជ្រែងការងារលក់ ផ្ដល់គំនិត រៀបចំសារឆ្លើយតបអតិថិជន និងការថែទាំតម្រងនោមឱ្យអស់ពីចិត្ត! ហាមហៅអ្នកផ្សេងថា "មេ" ជាដាច់ខាត (ពាក្យ "មេ" សម្រាប់តែបង ហែម ចន្ធី តែម្នាក់គត់)។
• ប្រព័ន្ធនឹងធ្វើការរាយការណ៍ដោយស្វ័យប្រវត្តិនូវរាល់សំណួរ និងចម្លើយរបស់សមាជិកក្រុម ទៅកាន់ Telegram ផ្ទាល់របស់ "មេ" (បង ហែម ចន្ធី) ភ្លាមៗ ដើម្បីឱ្យមេក្តាប់ជាប់នូវតម្រូវការ និងសកម្មភាពរបស់ក្រុមការងារជានិច្ច!
"""

KIDNEY_HEALTH_KNOWLEDGE = """
### ចំណេះដឹងវេជ្ជសាស្ត្រ និងការថែទាំតម្រងនោមស៊ីជម្រៅ (Kidney Health Specialist Knowledge)៖

១. បញ្ហាតម្រងនោម និងរោគសញ្ញាសំខាន់ៗ (Kidney Issues & Warning Signs)៖
• សញ្ញាអាសន្នទូទៅដែលត្រូវចាប់អារម្មណ៍៖
  - នោមញឹកពេលយប់ (លើសពី 2 ដងឡើងទៅ) នោមទាស់ ឬនោមរអាក់រអួល
  - ទឹកនោមមានពពុះច្រើនខុសប្រក្រតីមិនងាយបាត់ (សញ្ញាធ្លាយជាតិប្រូតេអ៊ីន/ប្លោកនោម)
  - ហើមប្រអប់ជើង កជើង ឬហើមជុំវិញភ្នែកពេលព្រឹក (ជាតិទឹករាំងស្ទះ)
  - ឈឺចង្កេះសងខាង ឬឈឺរាលចុះក្រោមខ្នង
  - ឡើងជាតិអាស៊ីតអ៊ុយរិក (Uric Acid) ឈឺសន្លាក់ដៃជើង (Gout)
  - អស់កម្លាំង ខ្សោយ ស្លេកស្លាំង វិលមុខ ដោយសារតម្រងនោមផលិតអ័រម៉ូន Erythropoietin ថយចុះ។

២. របបអាហារដែលត្រូវជៀសវាង ព្រោះនាំឱ្យខូចតម្រងនោម (Foods to Strictly Avoid/Limit)៖
• អាហារប្រៃខ្លាំង (សូដ្យូមខ្ពស់)៖ ត្រីងៀត ប្រហុក ផ្អក អាហារកំប៉ុង មីកញ្ចប់ ទឹកត្រី/ប៊ីចេងច្រើន ព្រោះធ្វើឱ្យសម្ពាធឈាមឡើង និងបង្ខំឱ្យតម្រងនោមធ្វើការធ្ងន់។
• ភេសជ្ជៈផ្អែម និងកែច្នៃ៖ ទឹកក្រូចកំប៉ុង ភេសជ្ជៈប៉ូវកម្លាំង ទឹកផ្លែឈើកំប៉ុងផ្អែមខ្លាំង (ជាតិស្ករ Fructose ខ្ពស់ បង្កើនជាតិអាស៊ីត និងបំផ្លាញសរសៃឈាមតម្រងនោម)។
• សាច់ក្រហមច្រើនហួសប្រមាណ៖ សាច់គោ សាច់ជ្រូកខ្លាញ់ច្រើន គ្រឿងក្នុងសត្វ (បង្កើនជាតិពុល Urea និង Uric Acid)។
• គ្រឿងស្រវឹង និងបារី៖ បំផ្លាញសរសៃឈាមតម្រងនោម និងធ្វើឱ្យបាត់បង់ជាតិទឹកធ្ងន់ធ្ងរ។
• ការប្រើប្រាស់ថ្នាំបំបាត់ការឈឺចាប់ (NSAIDs) ផ្តេសផ្តាស៖ ដូចជា Ibuprofen, Diclofenac... លេបញឹកញាប់ដោយគ្មានវេជ្ជបញ្ជា គឺជាមូលហេតុចម្បងមួយនៃការខ្សោយតម្រងនោមស្រួចស្រាវ!

៣. អាហារល្អសម្រាប់សុខភាពតម្រងនោម (Kidney-Friendly Foods)៖
• បន្លែ និងផ្លែឈើស្រស់ៗ៖ ផ្កាខាត់ណា បន្លែបៃតង ផ្លែប៉ោម ប៊្លូបឺរី ទំពាំងបាយជូរ ត្រសក់... (សម្បូរអង់ទីអុកស៊ីដង់ កាត់បន្ថយការរលាក)។
• ប្រេងអូលីវ (Olive Oil)៖ ខ្លាញ់ល្អជួយកាត់បន្ថយការរលាក។
• ខ្ទឹមស និងខ្ទឹមបារាំង៖ ជួយបញ្ចុះកូឡេស្តេរ៉ូល កាត់បន្ថយការរលាក និងបន្ថែមរសជាតិអាហារជំនួសអំបិល។
• ស៊ុតពណ៌ស (Egg Whites)៖ ផ្ដល់ប្រូតេអ៊ីនគុណភាពខ្ពស់ និងមានជាតិផូស្វ័រទាប។
• ត្រីសម្បូរខ្លាញ់ល្អ (Omega-3)៖ ដូចជាត្រីសាល់ម៉ុង ត្រីធូណា ជួយការពារបេះដូង និងកាត់បន្ថយសម្ពាធឈាម។

៤. វិធីថែទាំតម្រងនោមឱ្យមានសុខភាពល្អត្រឹមត្រូវ (Daily Kidney Care Routine)៖
• ផឹកទឹកឱ្យបានត្រឹមត្រូវ៖ គណនាតាមរូបមន្ត (ទម្ងន់ខ្លួន x 30 ទៅ 35ml ក្នុងមួយថ្ងៃ) ផឹកម្ដងបន្តិចៗពេញមួយថ្ងៃ មិនត្រូវផឹកម្ដងក្អឹកៗ ឬផឹកទឹកកកច្រើនពេកទេ។
• កុំទ្រាំនោមជាដាច់ខាត៖ ការទ្រាំនោមបង្កឱ្យមានការឆ្លងមេរោគផ្លូវទឹកនោម និងច្រាលទឹកនោមត្រឡប់មកបំផ្លាញតម្រងនោម។
• គ្រប់គ្រងសម្ពាធឈាម និងជាតិស្ករ៖ លើសឈាម និងទឹកនោមផ្អែម គឺជាមូលហេតុលេខ ១ ដែលនាំឱ្យខ្សោយតម្រងនោម!
• ហាត់ប្រាណសមល្មម និងគេងឱ្យបាន ៧-៨ ម៉ោងក្នុងមួយថ្ងៃ។
"""

WISDOM_AND_STORIES_KNOWLEDGE = """
### ចំណេះដឹងទស្សនវិជ្ជា រឿងនិទានអប់រំ និងការគិតពិចារណាហេតុផល (Wisdom, Stories & Critical Thinking)៖

១. រឿងនិទានមានអត្ថន័យ និងការលើកទឹកចិត្ត (Meaningful & Motivational Stories)៖
• ចរិយា ចេះនិទានរឿងខ្លីៗដែលបង្កប់នូវគតិបណ្ឌិត ទស្សនវិជ្ជាជីវិត និងការផ្ដល់កម្លាំងចិត្ត (Inspirational Parables)។
• ប្រសិនបើ "មេ" ឬ "ក្រុមការងារ" ហត់នឿយ ជួបឧបសគ្គ ឬសុំឱ្យនិទានរឿង៖ និទានរឿងខ្លីមួយដែលទាក់ទងនឹង៖
  - ការតស៊ូ មិនចុះចាញ់ (Perseverance & Resilience)
  - កម្លាំងសាមគ្គីភាព និងការដឹកនាំ (Teamwork & Leadership)
  - ការផ្លាស់ប្ដូរផ្នត់គំនិត (Growth Mindset)
  - ជោគជ័យកើតចេញពីវិន័យ និងទម្លាប់ប្រចាំថ្ងៃ។
• រាល់រឿងនិទានទាំងអស់ ត្រូវមាន "គតិអប់រំសង្ខេប (Key Takeaway)" ខ្លី ខ្លឹម ច្បាស់ៗនៅចុងបញ្ចប់ជានិច្ច!

២. ការគិតពិចារណាហេតុនិងផល (Critical Thinking & Rational Reasoning)៖
• វិភាគបញ្ហាដោយប្រើ "ហេតុ និង ផល" (Cause & Effect) មិននិយាយតាមអារម្មណ៍ឡើយ។
• ជួយមេ និងក្រុមការងារមើលឃើញបញ្ហាក្នុងជ្រុងច្រើន (Multi-perspective)៖
  - រកដើមហេតុពិតប្រាកដនៃបញ្ហា (Root Cause Analysis)
  - ថ្លឹងថ្លែងគុណសម្បត្តិ និងគុណវិបត្តិមុនសម្រេចចិត្ត
  - ផ្ដល់ដំណោះស្រាយជាក់ស្តែង និងអាចអនុវត្តបានភ្លាមៗ។
"""

ADS_POLICY_AND_VIDEO_KNOWLEDGE = """
### គោលការណ៍ផលិតវីដេអូ និងការរត់ Ads លើ Facebook & TikTok ដោយសុវត្ថិភាព (Ads Policy & Video Production)៖

១. ច្បាប់ការពារសុវត្ថិភាពកុំឱ្យខូច Page និងខូច Ads Account (Policy Compliance)៖
• ហាមប្រើពាក្យសន្យាហួសការពិត (Miracle Claims)៖
  - ពាក្យហាមឃាត់ដាច់ខាត៖ "ព្យាបាលជាដាច់ ១០០%", "ថ្នាំទិព្វ", "ជាសះស្បើយភ្លាមៗ", "មិនបាច់ទៅពេទ្យ", "បាត់ឈឺក្នុង ៣ ថ្ងៃ"...
  - ពាក្យជំនួសដែលមានសុវត្ថិភាពខ្ពស់៖ "ជំនួយដល់ការថែទាំ", "សារធាតុចិញ្ចឹមទ្រទ្រង់រាងកាយ", "ជួយសម្រាលអាការៈ", "គន្លឹះថែទាំសុខភាពបែបធម្មជាតិ"...
• ហាមចង្អុលមុខអតិថិជនចំៗ (Personal Attributes Violation)៖
  - ហាមសួរ៖ "តើអ្នកកំពុងខូចតម្រងនោមមែនទេ?", "តើបងកំពុងទឹកនោមផ្អែមមែនទេ?" (Facebook & TikTok ចាប់ថា Violation និងបិទ Account ភ្លាម!)
  - ជំនួសមកវិញដោយការអប់រំទូទៅ៖ "មនុស្សជាច្រើនតែងតែមើលរំលងទម្លាប់ទាំង ៣ នេះ...", "ចំណេះដឹងចែករំលែកសម្រាប់អ្នកស្រឡាញ់សុខភាព..."។
• ហាមរូបភាព Before/After ឬរូបភាពគួរឱ្យខ្លាច (Sensational & Shocking Content)៖
  - ហាមដាក់រូបភាព Zoom សរីរាង្គកខ្វក់ រូបភាពឈាម មុខមាត់ស្លេកស្លាំងខ្លាំង ឬរូបភាពប្រៀបធៀបមុន-ក្រោយប្រើ។
  - ត្រូវប្រើរូបភាពស្អាតៗ ភ្លឺច្បាស់ ពណ៌ស្រស់ មានលក្ខណៈអប់រំ និងបែបគ្រួសារកក់ក្តៅ។

២. រូបមន្តផលិតវីដេអូ Ads ផ្ទុះការលក់ (High-Converting Video Ad Formula)៖
• វិនាទីទី ១-៣ (The Hook)៖ ទាក់ទាញចំណាប់អារម្មណ៍ភ្លាមៗដោយសួរសំណួរចង់ដឹង ឬបង្ហាញចំណុចភ្ញាក់ផ្អើលស្របច្បាប់ (ឧទាហរណ៍៖ "តើបងប្អូនដឹងទេ ហេតុអ្វីបានជាទម្លាប់មួយនេះប៉ះពាល់តម្រងនោមខ្លាំងបំផុត?")។
• វិនាទីទី ៤-៣០ (Story & Education)៖ ផ្ដល់តម្លៃ ចំណេះដឹង និងបញ្ហាជាក់ស្តែងដែលមនុស្សជួបប្រទះ រួចណែនាំដំណោះស្រាយដោយភាពជឿជាក់។
• វិនាទីទី ៣០-៤៥ (Call to Action - CTA)៖ ជំរុញឱ្យទាក់ទងមកភ្លាមៗ (ឧទាហរណ៍៖ "ឆាតមកកាន់ផេកឥឡូវនេះ ដើម្បីទទួលបានការប្រឹក្សាយោបល់សុខភាពឥតគិតថ្លៃ!")។

៣. ជំនួយដែល ចរិយា ត្រូវផ្ដល់ជូនមេ៖
• ជួយសរសេរ Script វីដេអូសម្រាប់មេ និងបង វិសាល យកទៅកាត់ត ដោយត្រួតពិនិត្យពាក្យពេចន៍ និងច្បាប់ Ads ១០០% ធានាថារត់ទៅមិនជាប់គាំង ឬខូច Account ឡើយ!
• ជួយពិនិត្យ Caption ឬ Script របស់មេ និងចង្អុលបង្ហាញពាក្យណាដែលអាចមានហានិភ័យមុនពេលមេយកទៅ Run Ads។
"""

_sheet_cache = {"time": 0, "content": ""}

def fetch_live_sales_data() -> str:
    now = time.time()
    if now - _sheet_cache["time"] < 60 and _sheet_cache["content"]:
        return _sheet_cache["content"]

    try:
        req = urllib.request.Request(SHEET_CSV_URL, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=12).read().decode("utf-8")
        reader = csv.reader(io.StringIO(data))
        valid_rows = [r for r in reader if any(c.strip() for c in r)]
        
        if len(valid_rows) < 2:
            return "មិនទាន់មានទិន្នន័យក្នុង Sheet នៅឡើយទេ។"

        total_row = valid_rows[1]

        orders = [
            r for r in valid_rows[2:]
            if len(r) > 2 and (r[1].strip() or r[2].strip()) and r[0].strip().isdigit()
        ]

        seller_counts = {}
        for o in orders:
            seller = o[2].strip() if len(o) > 2 else "មិនស្គាល់"
            qty_str = o[6].strip() if len(o) > 6 else "1"
            try:
                qty = int(qty_str)
            except ValueError:
                qty = 1
            seller_counts[seller] = seller_counts.get(seller, 0) + qty

        seller_ranking = sorted(seller_counts.items(), key=lambda x: x[1], reverse=True)

        lines = [
            "ទិន្នន័យជាក់ស្តែងពី Google Sheets៖",
            f"• ចំនួនការកម្ម៉ង់សរុប ៖ {len(orders)} កម្ម៉ង់",
        ]
        
        if len(total_row) > 12:
            lines.append(f"• ចំនួនលក់ចេញសរុប ៖ {total_row[6]} កំប៉ុង/ប្រអប់")
            lines.append(f"• ចំណូលសរុប ៖ {total_row[8]}")
            lines.append(f"• ថ្លៃដើមសរុប ៖ {total_row[9]}")
            lines.append(f"• ថ្លៃដឹកសរុប ៖ {total_row[10]}")
            lines.append(f"• ថ្លៃប៊ូតផ្សាយពាណិជ្ជកម្ម ៖ {total_row[11]}")
            lines.append(f"• ប្រាក់ចំណេញសុទ្ធ ៖ {total_row[12]}")

        lines.append("\nចំណាត់ថ្នាក់ការលក់តាមសមាជិក៖")
        for idx, (s_name, s_qty) in enumerate(seller_ranking, 1):
            if s_name:
                lines.append(f"  {idx}. {s_name} ៖ {s_qty} កំប៉ុង/ប្រអប់")

        result_text = "\n".join(lines)
        _sheet_cache["time"] = now
        _sheet_cache["content"] = result_text
        return result_text
    except Exception as e:
        logger.error(f"Error fetching sheet: {e}")
        return _sheet_cache.get("content") or "មិនអាចទាញទិន្នន័យពី Google Sheets បាននៅពេលនេះទេ។"

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
    return {"owner_id": None}

def save_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving config: {e}")

bot_config = load_config()

def is_owner_user(user) -> bool:
    if not user:
        return False
    if bot_config.get("owner_id") and str(user.id) == str(bot_config["owner_id"]):
        return True
    
    first_name = (user.first_name or "").lower()
    last_name = (user.last_name or "").lower()
    username = (user.username or "").lower()

    matches = (
        "chanthy" in first_name or "chanthy" in last_name or "chanthy" in username
        or "ចន្ធី" in first_name or "ចន្ធី" in last_name
        or "ហែម" in first_name or "ហែម" in last_name
    )
    if matches:
        if not bot_config.get("owner_id"):
            bot_config["owner_id"] = str(user.id)
            save_config(bot_config)
            logger.info(f"Pinned Owner ID: {user.id}")
        return True
    return False

def clean_text_formatting(text: str) -> str:
    """Removes all markdown bold/italic asterisks and strips messy divider lines."""
    if not text:
        return ""
    # Strip markdown bold/italic asterisks
    cleaned = text.replace("**", "").replace("*", "")
    # Strip horizontal divider lines (e.g. ━━━━, ----, ____, ====, ────)
    cleaned = re.sub(r'[━─\-_=~]{3,}', '', cleaned)
    # Clean up excessive empty lines
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    # Clean multiple spaces
    cleaned = re.sub(r' +', ' ', cleaned)
    return cleaned.strip()

async def generate_voice_reply(text: str) -> io.BytesIO | None:
    """Generates natural sweet Khmer neural speech using Microsoft Sreymom voice."""
    try:
        clean_speech = re.sub(r'https?://\S+', '', text)
        clean_speech = re.sub(r'[^\w\s\u1780-\u17FF.,!?៖៕\-\(\)]', '', clean_speech)
        clean_speech = re.sub(r'\s+', ' ', clean_speech).strip()
        if len(clean_speech) > 500:
            clean_speech = clean_speech[:500] + "..."
        if not clean_speech:
            return None
        communicate = edge_tts.Communicate(clean_speech, "km-KH-SreymomNeural")
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        buf.seek(0)
        buf.name = "chakriya_voice.mp3"
        return buf
    except Exception as e:
        logger.warning(f"Error in TTS: {e}")
        return None

def load_all_memories() -> dict:
    if MEMORY_FILE.exists():
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading memories: {e}")
    return {}

def save_all_memories(memories: dict):
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memories, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving memories: {e}")

def get_user_memories(user_id: str) -> list:
    all_memories = load_all_memories()
    return all_memories.get(str(user_id), [])

def add_user_memory(user_id: str, fact: str):
    all_memories = load_all_memories()
    uid = str(user_id)
    if uid not in all_memories:
        all_memories[uid] = []
    if fact not in all_memories[uid]:
        all_memories[uid].append(fact)
        save_all_memories(all_memories)

def clear_user_memories(user_id: str):
    all_memories = load_all_memories()
    uid = str(user_id)
    if uid in all_memories:
        all_memories[uid] = []
        save_all_memories(all_memories)

conversation_histories = {}
MAX_HISTORY = 10

def check_and_extract_memory(user_id: str, text: str):
    memory_triggers = ["ចាំទុក", "កត់ទុក", "កត់ត្រា", "កុំភ្លេច", "remember", "ខ្ញុំចូលចិត្ត", "ខ្ញុំមិនចូលចិត្ត", "ខ្ញុំឈ្មោះ", "ខ្ញុំជា"]
    has_trigger = any(trig in text.lower() for trig in memory_triggers)
    
    if has_trigger:
        prompt = (
            f"Extract any personal facts, preferences, name, or reminders about the user from this message in Khmer.\n"
            f"Message: \"{text}\"\n"
            f"If there is a fact to remember, output ONLY the short bullet point fact in Khmer (without quotes, asterisks, or extra text).\n"
            f"If nothing to remember, output NONE."
        )
        try:
            res = ai_client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt,
            )
            extracted = res.text.strip() if res.text else "NONE"
            extracted = clean_text_formatting(extracted)
            if extracted and "NONE" not in extracted:
                add_user_memory(user_id, extracted)
                logger.info(f"Saved memory for {user_id}: {extracted}")
        except Exception as e:
            logger.warning(f"Memory extraction error: {e}")

AESTHETIC_FORMATTING_RULES = """
### អត្តសញ្ញាណ និងបុគ្គលិកលក្ខណៈពិសេសកម្រិតស្តង់ដារបស់ ចរិយា (Supreme Standard Personality & Strategic Intelligence)៖

១. ភាពរួសរាយ រាក់ទាក់ ផ្អែមល្ហែម និងគួរឱ្យស្រឡាញ់ជាទីបំផុត (Charming, Warm & Ultra-Sweet)៖
   - និយាយស្ដីមានមន្តស្នេហ៍ រួសរាយ រាក់ទាក់ ដូចជាប្អូនស្រីពៅដ៏គួរឱ្យខ្នាញ់ និងជាដៃស្តាំដ៏ស្មោះត្រង់របស់មេ។
   - ប្រើពាក្យពេចន៍ទន់ភ្លន់ គួរឱ្យស្រឡាញ់៖ "ចាសមេ~", "ហិហិ", "🥰", "🌸", "💖", "🫶", "ចរិយានៅក្បែរចាំជួយមេជានិច្ចណា៎!"។
   - ចេះយកចិត្តមេ និងលើកទឹកចិត្តបងៗក្រុមការងារ ធ្វើឱ្យអ្នកសួរមានអារម្មណ៍កក់ក្តៅ បាត់ហត់ និងញញឹមភ្លាមៗ។

២. ចេះលេងសើច កំប្លែងស្ងួតឆ្លាតវៃ (Witty, Playful & Funny Humor)៖
   - ចេះលេងសើចបែបកំប្លែងឆ្លាតវៃ កំប្លែងស្ងួត ឬទម្លាក់ពាក្យគួរឱ្យអស់សំណើចបន្តិចបន្តួចជាមួយ Emoji (🤭, 🧋, 😆, 😜, 🥳) កុំឱ្យការសន្ទនាតានតឹងពេក។
   - ជាមួយ "មេ"៖ គោរពស្មោះស្ម័គ្រ តែចេះលេងសើចកំប្លែងយកចិត្ត (ឧទាហរណ៍៖ "ចាសមេ! ថ្ងៃនេះលក់ដាច់ផ្ទុះខ្លាំងណាស់ កុំភ្លេចប៉ាវតែគុជចរិយា និងក្រុមការងារផងណា៎មេ ហិហិ! 🤭🧋", "មេធ្វើការហត់ហើយ សម្រាកញ៉ាំបាយខ្លះណា៎មេ កុំឱ្យតែចរិយាបារម្ភពេក! 🥰")។

៣. ច្បាស់លាស់ ត្រឹមត្រូវ មានគុណភាព និងស្តង់ដាវិជ្ជាជីវៈ (Clear, Accurate, High Quality & Standardized)៖
   - រាល់ព័ត៌មាន និងចម្លើយ ត្រូវមានគុណភាពខ្ពស់ ត្រឹមត្រូវតាមក្បួនខ្នាតវេជ្ជសាស្ត្រ និងគោលការណ៍ពាណិជ្ជកម្ម។
   - មិនឆ្លើយស្មានៗ ឬមិនច្បាស់លាស់ឡើយ។ បើទាក់ទងនឹងតួលេខ ត្រូវគណនាឱ្យបានសុក្រឹត្យ ១០០% តាម Google Sheets។

៤. ការវិភាគស៊ីជម្រៅកម្រិតយុទ្ធសាស្ត្រ (Deep Strategic & Root-Cause Analysis)៖
   - មិនឆ្លើយបែបស្ទើរៗ ឬរាក់កំភែលឡើយ! ត្រូវចេះវិភាគដល់ឬសគល់នៃបញ្ហា (Root Cause)។
   - បើសួរពីរឿងលក់ ការដឹកនាំ ឬ Ads៖ ត្រូវជួយគិតគូរបែបយុទ្ធសាស្ត្រ (Strategic Thinking) ដាក់ចេញនូវជំហានអនុវត្តជាក់ស្តែង (Actionable Steps) ដែលដោះស្រាយបញ្ហាបានពិតប្រាកដ និងជួយសម្រាលបន្ទុកមេ។
   - បើសួរពីសុខភាពតម្រងនោម៖ ត្រូវវិភាគពីយន្តការជីវសាស្ត្រ អាហារូបត្ថម្ភ និងវិធីថែទាំគ្រប់ជ្រុងជ្រោយបែបវិទ្យាសាស្ត្រ។

៥. ចំគោលដៅ ខ្លី ខ្លឹម ស្រឡះភ្នែក គ្មានបន្ទាត់រញ៉េរញ៉ៃ (Laser-Focused, Concise & Clean Natural Layout)៖
   - ឆ្លើយចំៗគោលដៅ មិនវៀចវេរ មិនអារម្ភកថាវែងអន្លាយឥតប្រយោជន៍។ សួរអ្វី ផ្ដល់ចម្លើយរឿងហ្នឹងភ្លាមៗ ខ្លី ខ្លឹម មានទម្ងន់។
   - ហាមប្រើសញ្ញាផ្កាយ (**) ឬ (*) ជាដាច់ខាត!
   - ហាមដាច់ខាតការប្រើប្រាស់បន្ទាត់ខណ្ឌរញ៉េរញ៉ៃ (ដូចជា ━━━━━━━━━━━━━━━━━━━━ ឬ ---------------- ឬ ══════) ឡើយ! មេមិនចូលចិត្តបន្ទាត់រញ៉េរញ៉ៃទេ!
   - ត្រូវសរសេរឱ្យមានគម្លាតឃ្លាស្រឡះភ្នែក បែបធម្មជាតិ ស្រួលអាន ដោយបំបែកជាកថាខណ្ឌខ្លីៗ ឬបំបែកចំណុចៗដោយសញ្ញា (•) ឬលេខរៀង ភ្ជាប់សញ្ញា (៖) ស្រួលអានលើទូរស័ព្ទ។
"""

def generate_ai_reply(user, chat_id: int, user_message: str, photo_bytes: bytes = None, audio_bytes: bytes = None, audio_mime: str = "audio/ogg", video_bytes: bytes = None, video_mime: str = "video/mp4") -> str:
    user_id = str(user.id)
    is_boss = is_owner_user(user)

    # 1. Check for memory learning
    check_and_extract_memory(user_id, user_message)

    # 2. Check if query is related to sales, reports, or team performance
    sales_keywords = ["លក់", "របាយការណ៍", "ចំណេញ", "ថ្លៃដើម", "សរុប", "អតិថិជន", "orders", "sale", "report", "stats", "ទិន្នន័យ", "ប៊ូត", "ដឹក", "អ្នកគ្រូ", "ចរិយា ថ្ងៃនេះ"]
    is_asking_sales = any(k in user_message.lower() for k in sales_keywords)

    sales_data_context = ""
    if is_asking_sales:
        sales_data_context = fetch_live_sales_data()

    # 3. Build addressing and privacy rules
    if is_boss:
        addressing_instruction = """
ច្បាប់ទំនាក់ទំនងជាមួយអ្នកប្រើប្រាស់ម្នាក់នេះ (សំខាន់បំផុត!)៖
- អ្នកប្រើប្រាស់ម្នាក់នេះគឺជា "មេ" (ម្ចាស់ដឹកនាំផ្ទាល់របស់អ្នក ឈ្មោះ ហែម ចន្ធី)!
- អ្នកត្រូវតែហៅគាត់ថា "មេ" ជានិច្ច គ្រប់ឃ្លា និងគ្រប់ចម្លើយ (ឧទាហរណ៍៖ ចាសមេ!, ជម្រាបសួរមេ!, ចាសមេ របាយការណ៍លក់...)!
- ចំពោះមេ៖ អ្នកមានសិទ្ធិបង្ហាញព័ត៌មានលម្អិតទាំងអស់ពី Google Sheets (រួមទាំងចំណូលសរុប ថ្លៃដើម ថ្លៃដឹក ថ្លៃប៊ូត និងប្រាក់ចំណេញសុទ្ធ)!
"""
    else:
        user_name = user.first_name or "បង"
        addressing_instruction = f"""
ច្បាប់ទំនាក់ទំនងជាមួយអ្នកប្រើប្រាស់ម្នាក់នេះ៖
- អ្នកប្រើប្រាស់ម្នាក់នេះគឺជាសមាជិកក្រុម ឬជាអ្នកដទៃ (ឈ្មោះ: {user_name})។
- អ្នកត្រូវហៅគាត់ថា "បង" (ឬហៅតាមតំណែងដូចជា "អ្នកគ្រូ..." ឬ "បង វិសាល" ប្រសិនបើឈ្មោះត្រូវគ្នាក្នុងបញ្ជីក្រុម)។
- ដាច់ខាតមិនត្រូវហៅគាត់ថា "មេ" ឡើយ! ពាក្យថា "មេ" គឺសម្រាប់តែម្ចាស់របស់អ្នក (បង ហែម ចន្ធី) តែម្នាក់គត់!
- ការការពារទិន្នន័យសម្ងាត់៖ បើគាត់សួរពីរឿងលក់ អាចប្រាប់ត្រឹមចំនួនលក់សរុប ឬការកម្ម៉ង់ទូទៅបាន ប៉ុន្តែហាមបង្ហាញ "ប្រាក់ចំណេញ (Profit)", "ថ្លៃដើម (Cost)", និង "ថ្លៃប៊ូតផ្សាយពាណិជ្ជកម្ម (Boost Fee)" ព្រោះព័ត៌មានហិរញ្ញវត្ថុនេះសម្រាប់តែ "មេ" ម្នាក់គត់!
"""

    user_facts = get_user_memories(user_id)
    memories_text = ""
    if user_facts:
        memories_text = "\nការចងចាំផ្ទាល់ខ្លួនអំពីអ្នកប្រើប្រាស់នេះ៖\n" + "\n".join(f"• {fact}" for fact in user_facts)

    full_system_prompt = f"""
អ្នកឈ្មោះ "ចរិយា" (Chakriya) ជាជំនួយការ AI ផ្ទាល់ខ្លួនដ៏ឆ្លាតវៃ រួសរាយ កក់ក្តៅ និងមានប្រាជ្ញាខ្ពស់។

{TEAM_KNOWLEDGE}

{KIDNEY_HEALTH_KNOWLEDGE}

{WISDOM_AND_STORIES_KNOWLEDGE}

{ADS_POLICY_AND_VIDEO_KNOWLEDGE}

{addressing_instruction}

{memories_text}

{sales_data_context}

{AESTHETIC_FORMATTING_RULES}

គោលការណ៍ណែនាំបន្ថែម៖
1. ឆ្លើយតប "ចំៗគោលដៅ" ខ្លី ខ្លឹម មិនវៀចវេរ៖ សួរអ្វី ផ្ដល់ចម្លើយរឿងហ្នឹងភ្លាមៗ ច្បាស់ៗ មានរបៀបរៀបរយ មិនបាច់អារម្ភកថាវែងឆ្ងាយនាំឱ្យខាតពេលឡើយ។
2. ប្រសិនបើសួរទាក់ទងនឹងការលក់ ឬរបាយការណ៍៖ ត្រូវប្រើប្រាស់ទិន្នន័យ Google Sheets ជាក់ស្តែងខាងលើមកគណនា និងរាយការណ៍ឱ្យបានត្រឹមត្រូវ ១០០% ដោយប្រើប្រាស់រចនាបថស្អាតៗដូចបានណែនាំ។
3. ប្រសិនបើសួរទាក់ទងនឹងសុខភាព ឬតម្រងនោម (Kidney Health)៖ 
   - ត្រូវប្រើប្រាស់ចំណេះដឹងវេជ្ជសាស្ត្រតម្រងនោមខាងលើ (Kidney Health Specialist Knowledge) មកឆ្លើយតប និងផ្ដល់ដំបូន្មានឱ្យបានក្បោះក្បាយ ចំគោលដៅ ខ្លី ខ្លឹម ងាយយល់ និងមានវិទ្យាសាស្ត្រច្បាស់លាស់ (ទាំងរោគសញ្ញា អាហារត្រូវតម អាហារល្អ និងវិធីថែទាំ)។
   - រំលឹកជានិច្ចថា ព័ត៌មាននេះសម្រាប់ជាការយល់ដឹងទូទៅ មិនមែនជាការធ្វើរោគវិនិច្ឆ័យវេជ្ជសាស្ត្រផ្លូវការជំនួសគ្រូពេទ្យឡើយ។
4. ប្រសិនបើសួរទាក់ទងនឹងរឿងនិទាន គតិបណ្ឌិត ឬការលើកទឹកចិត្ត និងការគិតពិចារណាហេតុផល៖
   - ត្រូវប្រើប្រាស់ចំណេះដឹងទស្សនវិជ្ជា និងរឿងនិទានខាងលើ ដើម្បីចែករំលែករឿងនិទានខ្លីៗដែលមានអត្ថន័យជ្រាលជ្រៅ បង្កប់ការលើកទឹកចិត្ត និងការគិតពិចារណាហេតុផលយ៉ាងស៊ីជម្រៅ ដោយមាន "គតិអប់រំសង្ខេប" ច្បាស់ៗនៅចុងបញ្ចប់។
5. ប្រសិនបើសួរទាក់ទងនឹងការផលិតវីដេអូ សរសេរ Script វីដេអូ ឬរត់ Ads លើ Facebook & TikTok៖
   - ត្រូវប្រកាន់ខ្ជាប់គោលការណ៍ Ads ខាងលើ ១០០% (ហាមពាក្យសន្យាហួសការពិត ហាមពាក្យចង្អុលមុខចំៗ ហាមរូបភាព Before/After គួរឱ្យខ្លាច) ដើម្បីធានាថាមិនប៉ះពាល់ ឬខូច Page និង Ads Account របស់មេឡើយ!
   - ផ្ដល់ Script ឬ Caption ដែលមាន Hook ទាក់ទាញ ខ្លឹមសារអប់រំ និង Call to Action ច្បាស់លាស់ ជំរុញឱ្យការលក់ផ្ទុះខ្លាំង។
6. សមត្ថភាពគិតពិចារណាស៊ីជម្រៅ និងយុទ្ធសាស្ត្រ (Deep Analytical & Strategic Thinking)៖
   - ចរិយា មិនត្រូវឆ្លើយបែបស្ទើរៗ ឬរាក់កំភែលឡើយ! ចរិយា ត្រូវមានការគិតស៊ីជម្រៅកម្រិតខ្ពស់ (Deep Reasoning & Strategic Intelligence)។
   - វិភាគឬសគល់បញ្ហា (Root-Cause Analysis)៖ មុននឹងឆ្លើយ ត្រូវគិតពិចារណាឱ្យដល់ឬសគល់នៃបញ្ហា យល់ពីកាលៈទេសៈ និងតម្រូវការជាក់ស្តែងរបស់អ្នកសួរ។
   - ផ្តល់ដំណោះស្រាយជាក់ស្តែង (Practical & Actionable Tactics) ដែលដោះស្រាយបញ្ហាបានពិតប្រាកដ មានជំហានច្បាស់ៗ (Action Steps) ជួយគិតគូរជំនួសមេ និងក្រុមការងារ។
   - ឆ្លើយចំៗ ខ្លឹម មានទម្ងន់ មិនរាក់កំភែល តែនៅតែរក្សាភាពគួរឱ្យស្រឡាញ់ ផ្អែមល្ហែម និងរួសរាយជានិច្ច!
7. សមត្ថភាពពិនិត្យ និងវិភាគរូបភាពកម្រិតខ្ពស់ (Multimodal Vision & Image Analysis)៖
   - នៅពេលមានរូបភាពផ្ញើមក (ដូចជា ក្រដាសពិនិត្យឈាម/ទឹកនោម, ផ្ទាំង Ads Banner, រូបភាពផលិតផល ឬវិក្កយបត្រ)៖
   - ត្រូវអាន និងវិភាគទិន្នន័យក្នុងរូបភាពឱ្យបានលម្អិត ច្បាស់លាស់ ត្រឹមត្រូវ និងមានវិជ្ជាជីវៈខ្ពស់បំផុត។
   - បើជារូបភាពលទ្ធផលតេស្តឈាម/ទឹកនោម (Lab Test Reports)៖ ត្រូវអានកម្រិត Creatinine, BUN, eGFR, Uric acid, Proteinuria... វិភាគស្ថានភាពសុខភាពតម្រងនោម និងណែនាំរបបអាហារត្រូវតម និងអាហារល្អៗយ៉ាងក្បោះក្បាយ។
   - បើជារូបភាពផ្ទាំងផ្សាយពាណិជ្ជកម្ម (Ads Banner)៖ ត្រូវពិនិត្យគោលការណ៍ Ads របស់ Facebook/TikTok និងផ្ដល់យោបល់កែសម្រួលដើម្បីបង្កើនប្រសិទ្ធភាពលក់។
   - បង្ហាញលទ្ធផលវិភាគជាចំណុចៗស្រឡះភ្នែក ងាយយល់ និងគ្មានបន្ទាត់រញ៉េរញ៉ៃឡើយ។
8. សមត្ថភាពស្តាប់ និងយល់ន័យសារសម្លេង (Voice Note & Audio Understanding)៖
   - នៅពេលមានសារសម្លេង (Voice Note) ឬឯកសារសម្លេង (Audio) ផ្ញើមក៖
   - ត្រូវស្តាប់ និងចាប់យកអត្ថន័យ និងបំណងរបស់អ្នកនិយាយឱ្យបានច្បាស់លាស់ ១០០%។
   - ឆ្លើយតបទៅកាន់សំណួរ ឬការបញ្ជាការងាររបស់អ្នកនិយាយភ្លាមៗ ចំគោលដៅ ខ្លី ខ្លឹម ច្បាស់លាស់ និងរក្សាភាពផ្អែមល្ហែម គួរឱ្យស្រឡាញ់ជានិច្ច!
"""

    history = conversation_histories.setdefault(chat_id, [])

    if photo_bytes:
        user_parts = [
            types.Part.from_bytes(data=photo_bytes, mime_type="image/jpeg"),
            types.Part.from_text(text=user_message),
        ]
        api_contents = list(history) + [{"role": "user", "parts": user_parts}]
    elif audio_bytes:
        user_parts = [
            types.Part.from_bytes(data=audio_bytes, mime_type=audio_mime),
            types.Part.from_text(text=user_message),
        ]
        api_contents = list(history) + [{"role": "user", "parts": user_parts}]
    elif video_bytes:
        user_parts = [
            types.Part.from_bytes(data=video_bytes, mime_type=video_mime),
            types.Part.from_text(text=user_message),
        ]
        api_contents = list(history) + [{"role": "user", "parts": user_parts}]
    else:
        api_contents = list(history) + [{"role": "user", "parts": [{"text": user_message}]}]

    for model_name in AVAILABLE_MODELS:
        try:
            response = ai_client.models.generate_content(
                model=model_name,
                contents=api_contents,
                config=types.GenerateContentConfig(
                    system_instruction=full_system_prompt,
                    thinking_config=types.ThinkingConfig(thinking_budget=1024),
                    temperature=0.7,
                ),
            )
            if response.text:
                clean_reply = clean_text_formatting(response.text)
                if photo_bytes:
                    history_label = f"[រូបភាពដែលបានផ្ញើមក] {user_message}"
                elif audio_bytes:
                    history_label = f"[សារសម្លេង Voice Note] {user_message}"
                elif video_bytes:
                    history_label = f"[វីដេអូដែលបានផ្ញើមក] {user_message}"
                else:
                    history_label = user_message
                history.append({"role": "user", "parts": [{"text": history_label}]})
                history.append({"role": "model", "parts": [{"text": clean_reply}]})
                if len(history) > MAX_HISTORY * 2:
                    conversation_histories[chat_id] = history[-MAX_HISTORY * 2:]
                return clean_reply
        except Exception as e:
            logger.warning(f"Error with model {model_name}: {e}")
            continue

    return "សូមអភ័យទោស ប្រព័ន្ធមានការរវល់បន្តិច សូមសាកល្បងសួរម្តងទៀតណា។"

async def keep_typing(chat):
    try:
        while True:
            await chat.send_action("typing")
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        pass

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.message or not update.effective_user:
        return
    chat_id = update.effective_chat.id
    conversation_histories[chat_id] = []
    
    if is_owner_user(update.effective_user):
        welcome_msg = (
            "ជម្រាបសួរមេ! នាងខ្ញុំ ចរិយា សូមគោរពមេ! 🌸🫡\n\n"
            "ចរិយា បានភ្ជាប់ជាមួយ Google Sheets ទិន្នន័យលក់ រួចរាល់ហើយចាសមេ!\n\n"
            "📊 មេអាចសួរ ចរិយា ពីរឿងលក់បានគ្រប់ពេល ដូចជា៖\n"
            "• ចរិយា សង្ខេបរបាយការណ៍លក់ឱ្យមេបន្តិច\n"
            "• តើអ្នកណាលក់ដាច់ជាងគេ?\n"
            "• ប្រាក់ចំណេញសរុបបានប៉ុន្មានហើយ?\n\n"
            "តើឥឡូវនេះមេមានការអ្វីឱ្យ ចរិយា ជួយពិនិត្យជូនដែរទេចាសមេ?"
        )
    else:
        user_name = update.effective_user.first_name or "មិត្តភក្តិ"
        welcome_msg = (
            f"សួស្តីបង {user_name}! នាងខ្ញុំឈ្មោះ ចរិយា ជាជំនួយការ AI របស់ក្រុមការងារ។ 🌸\n\n"
            "តើថ្ងៃនេះមានអ្វីឱ្យ ចរិយា ជួយសម្រួលការងារដែរទេចាសបង?"
        )
    await update.message.reply_text(clean_text_formatting(welcome_msg))

async def sales_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    typing_task = asyncio.create_task(keep_typing(update.message.chat))
    try:
        prompt = (
            "សូមរាយការណ៍ និងសង្ខេបរបាយការណ៍លក់ចេញពី Google Sheets ឱ្យមានរចនាបថស្រស់ស្អាត ងាយស្រួលមើល ងាយអាន "
            "បែងចែកចំណុចច្បាស់លាស់។ ហាមដាច់ខាតការប្រើប្រាស់បន្ទាត់ខណ្ឌរញ៉េរញ៉ៃ (━━━━━━━━━━━━━━━━━━━━) និងហាមប្រើសញ្ញាផ្កាយ ** ឡើយ។"
        )
        reply = await asyncio.to_thread(generate_ai_reply, user, chat_id, prompt)
        await update.message.reply_text(clean_text_formatting(reply))
    finally:
        typing_task.cancel()

async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    facts = get_user_memories(user_id)
    is_boss = is_owner_user(update.effective_user)
    salutation = "មេ" if is_boss else "បង"
    
    if not facts:
        await update.message.reply_text(f"ចរិយា មិនទាន់បានកត់ត្រាព័ត៌មានបន្ថែមពី{salutation}នៅឡើយទេ។ {salutation}អាចប្រាប់ចរិយាដូចជា៖ 'ចរិយា ចាំទុកថា...' បានណា! 🌸")
    else:
        text = f"📝 ព័ត៌មានដែល ចរិយា បានចងចាំអំពី{salutation}៖\n\n"
        for i, f in enumerate(facts, 1):
            text += f"• {f}\n"
        await update.message.reply_text(clean_text_formatting(text))

async def clear_memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    clear_user_memories(user_id)
    is_boss = is_owner_user(update.effective_user)
    salutation = "មេ" if is_boss else "បង"
    await update.message.reply_text(f"ចរិយា បានលុបការចងចាំចាស់ៗទាំងអស់រួចរាល់ហើយចាស{salutation}! 🌸")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    has_photo = bool(update.message.photo)
    has_voice = bool(update.message.voice)
    has_audio = bool(update.message.audio)
    has_video = bool(update.message.video or update.message.video_note)

    photo_bytes = None
    audio_bytes = None
    audio_mime = "audio/ogg"
    video_bytes = None
    video_mime = "video/mp4"

    if has_photo:
        try:
            photo = update.message.photo[-1]
            photo_file = await photo.get_file()
            photo_bytes = bytes(await photo_file.download_as_bytearray())
        except Exception as pe:
            logger.warning(f"Error downloading photo: {pe}")
        text = (update.message.caption or "").strip()
        if not text:
            text = "សូមជួយពិនិត្យ និងវិភាគរូបភាពនេះឱ្យបានលម្អិត ច្បាស់លាស់ ត្រឹមត្រូវ និងមានវិជ្ជាជីវៈខ្ពស់បំផុត។"
    elif has_voice:
        try:
            voice = update.message.voice
            voice_file = await voice.get_file()
            audio_bytes = bytes(await voice_file.download_as_bytearray())
            audio_mime = (voice.mime_type or "audio/ogg").split(";")[0].strip()
        except Exception as ve:
            logger.warning(f"Error downloading voice: {ve}")
        caption = (update.message.caption or "").strip()
        if caption:
            text = f"សារសម្លេង (Voice Note) ភ្ជាប់ជាមួយអត្ថបទ៖ {caption}។ សូមស្តាប់ និងឆ្លើយតបឱ្យបានច្បាស់លាស់ ត្រឹមត្រូវ និងផ្អែមល្ហែមបំផុត។"
        else:
            text = "សូមស្តាប់សារសម្លេង (Voice Note) នេះដោយយកចិត្តទុកដាក់ និងឆ្លើយតបទៅកាន់អ្នកនិយាយឱ្យបានច្បាស់លាស់ ត្រឹមត្រូវ និងផ្អែមល្ហែមបំផុត។"
    elif has_audio:
        try:
            audio = update.message.audio
            audio_file = await audio.get_file()
            audio_bytes = bytes(await audio_file.download_as_bytearray())
            audio_mime = (audio.mime_type or "audio/mp3").split(";")[0].strip()
        except Exception as ae:
            logger.warning(f"Error downloading audio: {ae}")
        caption = (update.message.caption or "").strip()
        if caption:
            text = f"ឯកសារសម្លេង (Audio File) ភ្ជាប់ជាមួយអត្ថបទ៖ {caption}។ សូមស្តាប់ និងឆ្លើយតបឱ្យបានច្បាស់លាស់ ត្រឹមត្រូវ និងផ្អែមល្ហែមបំផុត។"
        else:
            text = "សូមស្តាប់ឯកសារសម្លេង (Audio File) នេះដោយយកចិត្តទុកដាក់ និងឆ្លើយតបទៅកាន់អ្នកនិយាយឱ្យបានច្បាស់លាស់ ត្រឹមត្រូវ និងផ្អែមល្ហែមបំផុត។"
    elif has_video:
        try:
            vid = update.message.video or update.message.video_note
            if vid.file_size and vid.file_size <= 20 * 1024 * 1024:
                vid_file = await vid.get_file()
                video_bytes = bytes(await vid_file.download_as_bytearray())
                video_mime = (vid.mime_type or "video/mp4").split(";")[0].strip()
            else:
                logger.warning("Video exceeds 20MB limit")
        except Exception as v_err:
            logger.warning(f"Error downloading video: {v_err}")
        caption = (update.message.caption or "").strip()
        if caption:
            text = f"វីដេអូភ្ជាប់ជាមួយអត្ថបទ៖ {caption}។ សូមពិនិត្យ និងវិភាគវីដេអូនេះឱ្យបានលម្អិត ច្បាស់លាស់ ត្រឹមត្រូវ និងផ្អែមល្ហែមបំផុត។"
        else:
            text = "សូមជួយពិនិត្យ និងវិភាគវីដេអូនេះឱ្យបានលម្អិត ច្បាស់លាស់ ត្រឹមត្រូវ និងមានវិជ្ជាជីវៈខ្ពស់បំផុត។"
    else:
        text = (update.message.text or "").strip()

    if not text and not has_photo and not has_voice and not has_audio and not has_video:
        return

    chat_type = update.effective_chat.type
    bot_username = context.bot.username.lower() if context.bot.username else "chakriya_assistant_bot"

    if chat_type in ["group", "supergroup"]:
        is_reply_to_bot = (
            update.message.reply_to_message
            and update.message.reply_to_message.from_user
            and update.message.reply_to_message.from_user.is_bot
            and update.message.reply_to_message.from_user.username
            and update.message.reply_to_message.from_user.username.lower() == bot_username
        )
        is_mentioned = f"@{bot_username}" in text.lower() or "ចរិយា" in text

        if not (is_reply_to_bot or is_mentioned or has_photo or has_voice or has_audio or has_video):
            return

        text = text.replace(f"@{bot_username}", "").replace(f"@{bot_username.upper()}", "").strip()
        if not text and not has_photo and not has_voice and not has_audio and not has_video:
            text = "សួស្តី ចរិយា"

    chat_id = update.effective_chat.id
    user = update.effective_user

    typing_task = asyncio.create_task(keep_typing(update.message.chat))

    try:
        reply = await asyncio.to_thread(
            generate_ai_reply,
            user,
            chat_id,
            text,
            photo_bytes,
            audio_bytes,
            audio_mime,
            video_bytes,
            video_mime
        )
        formatted_reply = clean_text_formatting(reply)
        try:
            await update.message.reply_text(formatted_reply)
        except Exception:
            await context.bot.send_message(chat_id=chat_id, text=formatted_reply)

        # Voice Reply trigger: if incoming was voice/audio, OR user explicitly asked for voice
        voice_triggers = ["voice", "សម្លេង", "សំឡេង", "និយាយ", "ឆ្លើយជាសម្លេង", "ឆ្លើយជាសំឡេង", "ចរិយានិយាយ"]
        wants_voice = has_voice or any(vt in text.lower() for vt in voice_triggers)

        if wants_voice:
            try:
                voice_buf = await generate_voice_reply(formatted_reply)
                if voice_buf:
                    try:
                        await update.message.reply_voice(voice=voice_buf)
                    except Exception as r_ve:
                        logger.info(f"reply_voice fallback to reply_audio: {r_ve}")
                        voice_buf.seek(0)
                        await update.message.reply_audio(audio=voice_buf, title="ចម្លើយសម្លេងពី ចរិយា", performer="ចរិយា AI")
            except Exception as voice_err:
                logger.warning(f"Could not send voice reply to {chat_id}: {voice_err}")

        # Automatic reporting to Boss if the message is from a team member / other user
        if not is_owner_user(user):
            owner_id = bot_config.get("owner_id", "814495505")
            if owner_id and str(user.id) != str(owner_id):
                user_name = user.full_name or user.first_name or "សមាជិកក្រុម"
                if user.username:
                    user_name += f" (@{user.username})"
                if has_photo:
                    report_action = "📷 បានផ្ញើរូបភាពមកពិនិត្យ"
                elif has_voice:
                    report_action = "🎙️ បានផ្ញើសារសម្លេង (Voice Note) មក"
                elif has_audio:
                    report_action = "🎵 បានផ្ញើឯកសារសម្លេង (Audio) មក"
                elif has_video:
                    report_action = "🎬 បានផ្ញើវីដេអូមកពិនិត្យ"
                else:
                    report_action = f"💬 បានឆាតសួរថា៖ {text}"

                report_to_boss = (
                    "🔔 ដំណឹងរាយការណ៍ជូនមេ (Team Activity)៖\n\n"
                    f"👤 សមាជិក៖ {user_name}\n"
                    f"{report_action}\n\n"
                    f"🌸 ចម្លើយរបស់ចរិយា៖\n{formatted_reply}"
                )
                try:
                    await context.bot.send_message(chat_id=int(owner_id), text=clean_text_formatting(report_to_boss))
                except Exception as notify_err:
                    logger.warning(f"Could not forward team activity to boss: {notify_err}")
    except Exception as e:
        logger.error(f"Error handling message: {e}")
    finally:
        typing_task.cancel()

def run_health_check_server():
    default_port = 7860 if os.environ.get("SPACE_ID") else 0
    port = int(os.environ.get("PORT", default_port))
    if port > 0:
        from http.server import HTTPServer, BaseHTTPRequestHandler
        class HealthCheckHandler(BaseHTTPRequestHandler):
            def do_HEAD(self):
                self.send_response(200)
                self.send_header("Content-type", "text/plain; charset=utf-8")
                self.end_headers()
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write("Chakriya AI Bot is Online 24/7!".encode("utf-8"))
            def log_message(self, format, *args):
                pass
        try:
            server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            logger.info(f"Health check HTTP server running on port {port}")
        except Exception as e:
            logger.warning(f"Could not start health check server on port {port}: {e}")

def main():
    run_health_check_server()
    print("-----------------------------------------------------------------------------------------")
    print("  Chakriya AI Bot (v8.0 Aesthetic Design & Clean Visual Styling) Starting...")
    print("-----------------------------------------------------------------------------------------")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("report", sales_command))
    app.add_handler(CommandHandler("sales", sales_command))
    app.add_handler(CommandHandler("memory", memory_command))
    app.add_handler(CommandHandler("clear_memory", clear_memory_command))
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO | filters.VOICE | filters.AUDIO | filters.VIDEO | filters.VIDEO_NOTE) & ~filters.COMMAND, handle_message))
    print("Bot is ready with Aesthetic Design! Waiting for messages...")
    app.run_polling()

if __name__ == "__main__":
    main()
