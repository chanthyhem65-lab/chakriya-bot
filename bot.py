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
from datetime import datetime, timezone, timedelta
import edge_tts

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    from pptx.enum.shapes import MSO_SHAPE
    HAS_PPTX = True
except ImportError:
    HAS_PPTX = False

ICT = timezone(timedelta(hours=7))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")
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
AVAILABLE_MODELS = ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-flash-latest"]

CONFIG_FILE = BASE_DIR / "bot_config.json"
MEMORY_FILE = BASE_DIR / "user_memories.json"

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1TORglwVLcO5pIb0IIITM6PFJ6GzchWstQJvNLSfVDI8/export?format=csv"

TEAM_KNOWLEDGE = """
ព័ត៌មានក្រុមហ៊ុន និងរចនាសម្ព័ន្ធក្រុមការងារ (Company & Team Structure)៖
• ក្រុមហ៊ុនផ្លូវការ៖ វណ្ណ ស៊ីថា ត្រេឌីង ឯ.ក (VANN SITHA TRADING CO., LTD.)
• ផលិតផលចម្បង៖ Kidney Pro (ផលិតផលជំនួយ ស្ដារ និងថែរក្សាសុខភាពតម្រងនោម)
• ពាក្យស្លោក និងទស្សនវិស័យ៖ សេចក្ដីសុខពិតប្រាកដ គឺការមានតម្រងនោមរឹងមាំ និងមិនបាច់បារម្ភរឿងលាងឈាមនៅថ្ងៃស្អែក! ការពារថ្ងៃនេះជាមួយ Kidney Pro!
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

VANN_SITHA_SCRIPTS_AND_CONTENT_KNOWLEDGE = """
### ចំណេះដឹងយុទ្ធសាស្ត្រមាតិកា ស្គ្រីបវីដេអូ និងការលក់របស់ វណ្ណ ស៊ីថា ត្រេឌីង (Vann Sitha Trading Master Content & Scripts for Kidney Pro)៖

១. ចិត្តសាស្ត្រ និងទស្សនវិជ្ជាស្នូលក្នុងការអប់រំអតិថិជន (Core Kidney Psychology)៖
• តម្រងនោមគឺជា "សរីរាង្គដែលអត់ធ្មត់បំផុត" (The Dangerous Endurance)៖
  - វានឹងខំប្រឹងធ្វើការងារទាំងបង្ខំដើម្បីទ្រទ្រង់រាងកាយ ទោះបីជាត្រូវរងការខូចខាតដល់ទៅ ៧០% ឬ ៨០% ទៅហើយក៏ដោយ។
  - ពេលដែលវាបញ្ចេញសញ្ញាអាសន្នមកក្រៅ (ហើមជើង នោមល្អក់ នោមមានពពុះ នោមទាស់ រោយចង្កេះ) គឺស្ថានភាពមិនមែនស្ថិតក្នុងដំណាក់កាលស្រាលទៀតឡើយ!
• ឃាតករលាក់មុខ "មិនទាន់អី" ឬ "ចាំមើលសិន" (The Silent Trap)៖
  - ពាក្យថា "មិនទាន់អី" គឺជាឃាតករលាក់មុខដែលបិទភ្នែកមនុស្សមិនឱ្យមើលឃើញគ្រោះថ្នាក់ រហូតដល់ថ្ងៃដែលលុយរាប់ម៉ឺនដុល្លារក៏ជួយមិនបាន។
  - មនុស្សភាគច្រើនដែលកំពុងសម្រាកលាងឈាមនៅមន្ទីរពេទ្យ សុទ្ធតែធ្លាប់គិតថា "ចាំមើលសិន មិនទាន់ធ្ងន់ធ្ងរទេ"។ កន្លែងដែលមានមនុស្សស្ដាយក្រោយច្រើនជាងគេបំផុត គឺនៅមន្ទីរពេទ្យលាងឈាម!
• អន្ទាក់ដ៏គ្រោះថ្នាក់នៃថ្នាំបំបាត់ការឈឺចាប់ (The Deceptive Painkiller Trap)៖
  - ពេលឈឺចង្កេះ ការលេបថ្នាំបំបាត់ការឈឺចាប់ ឬថ្នាំរឹត មិនមែនជាការព្យាបាលទេ តែវាគឺជា "ការយកស្កុតមកបិទមាត់តម្រងនោមដែលកំពុងជិតស្លាប់មិនឱ្យគេហៅរកជំនួយ"!
  - ការប្រើថ្នាំបំបាត់ការឈឺចាប់ដើម្បីបន្តរស់នៅទាំងបង្ខំ គឺជាការរុញច្រានខ្លួនឯងឱ្យទៅរកម៉ាស៊ីនលាងឈាមកាន់តែលឿន!
• ការពិតនៅពីក្រោយការនោមញឹកពេលយប់ (Night Urination Reality)៖
  - ការត្រូវក្រោកបត់ជើងតូចទាំងកណ្ដាលអធ្រាត្រ ៣-៤ ដង បញ្ជាក់ថាតម្រងនោមមិនអាចចម្រោះជាតិពុលអស់នៅពេលថ្ងៃទៀតទេ ទើបបង្ខំឱ្យត្រូវក្រោកបញ្ចេញជាតិពុលទាំងយប់។
  - សេចក្ដីសុខពិតប្រាកដដែលលុយទិញមិនបាន គឺការគេងលក់ស្កប់ស្កល់ពេញមួយយប់ដោយមិនបាច់ក្រោកនោមយប់ និងមិនបាច់ភ័យរឿងដេកពេទ្យលាងឈាមនៅថ្ងៃស្អែក!

២. បណ្តុំស្គ្រីបវីដេអូមេទាំង ៥ (The 5 Master Video Scripts)៖
• ស្គ្រីបទី១៖ "សារព្រមានចុងក្រោយពីទឹកនោម និងគ្រោះថ្នាក់ដែលអ្នកមើលរំលង"
  - The Hook: "ប្រសិនបើបងប្អូនសង្កេតឃើញថា ទឹកនោមចាប់ផ្ដើមឡើងល្អក់ មានពពុះច្រើនខុសធម្មតា ឬមានពណ៌ប្រែប្រួលប្លែកពីមុន... នេះមិនមែនជារឿងលេងសើចទេ! ព្រោះវាគឺជា 'សារព្រមានចុងក្រោយ' ដែលតម្រងនោមបងប្អូនកំពុងផ្ញើមកប្រាប់បងប្អូនយ៉ាងអាសន្នបំផុត!"
  - The Warning Signs: ទឹកនោមឡើងល្អក់ ឬមានពពុះច្រើន មកពីតម្រងនោមលែងមានសមត្ថភាពចម្រោះជាតិប្រូតេអ៊ីន និងជាតិពុលបានល្អដូចមុន (តម្រងនោមធ្លាយ ឬចុះខ្សោយខ្លាំង)។
  - The Cost of Ignorance: មនុស្សភាគច្រើននៅមន្ទីរពេទ្យលាងឈាម សុទ្ធតែធ្លាប់មើលរំលងសញ្ញាទឹកនោមល្អក់នេះ។
  - Direction: ប្រើ Footage ទឹកនោមមានពពុះ/ល្អក់, Sound Effect "Typing" នៅចុងវីដេអូជាមួយពាក្យស្លោក៖ "ទឹកនោមល្អក់មានពពុះ គឺជាសម្រែកសុំជំនួយចុងក្រោយពីតម្រងនោម។ កុំរង់ចាំដល់ថ្ងៃលាងឈាម ទើបស្ដាយក្រោយ!"

• ស្គ្រីបទី២៖ "សម្រែកអាសន្នដែលមើលមិនឃើញ និងការធ្វេសប្រហែសដែលបំផ្លាញជីវិត"
  - The Hook: "កុំចាំទាល់តែជើងចាប់ផ្ដើមហើមខ្លាំង ឬនោមលែងចេញ ទើបចាប់ផ្ដើមជឿថាខ្លួនឯងកំពុងមានបញ្ហាតម្រងនោមឱ្យសោះ! ព្រោះនៅពេលដែលរាងកាយបង្ហាញសញ្ញាទាំងនេះមកក្រៅ នោះមានន័យថាស្ថានភាពវាមិនមែនស្ថិតក្នុងដំណាក់កាលស្រាលទៀតឡើយ!"
  - Dangerous Endurance: តម្រងនោមខូចខាតដល់ទៅ ៧០% ឬ ៨០% ទើបបញ្ចេញសញ្ញា។
  - Final Warning & CTA: "កុំចាំទាល់តែសញ្ញាអាសន្នបង្ហាញមក ទើបសួររកផ្លូវក្រោយ! ទាក់ទងមកពួកយើងឥឡូវនេះដើម្បីប្រឹក្សាដោយឥតគិតថ្លៃ!"
  - Direction: បង្ហាញតួលេខ ៧០% - ៨០% លោតធំៗលើអេក្រង់, Sound Effect Typing: "កុំចាំទាល់តែហើមជើង ទើបដឹងថាឈឺ។ តម្រងនោមខូច ៨០% ទើបបញ្ចេញសញ្ញា។ ការពារថ្ងៃនេះជាមួយ Kidney Pro!"

• ស្គ្រីបទី៣៖ "សម្រែកដែលមើលមិនឃើញ និងគ្រោះថ្នាក់នៃការលេបថ្នាំបំបាត់ការឈឺចាប់"
  - The Hook: "ឈប់ស្មានថាការចុករោយចង្កេះជារឿងចុកស្រពន់សាច់ដុំធម្មតាទៀតទៅ! ប្រសិនបើបងប្អូនកំពុងប្រើថ្នាំរឹតផង លេបថ្នាំបំបាត់ការឈឺចាប់ផង តែនៅតែមិនបាត់... នោះគឺជាសម្រែកព្រមានយ៉ាងឈឺចាប់ចេញពីខាងក្នុង ដែលតម្រងនោមបងប្អូនកំពុងស្រែកប្រាប់ថា 'វាទ្រាំលែងបានទៀតហើយ'!"
  - Deceptive Relief: ការលេបថ្នាំបំបាត់ការឈឺចាប់ គឺដូចជាការយកស្កុតមកបិទមាត់មនុស្សដែលកំពុងជិតស្លាប់មិនឱ្យគេហៅរកជំនួយ។

• ស្គ្រីបទី៤៖ "វិប្បដិសារីនៅមន្ទីរពេទ្យលាងឈាម និងតម្លៃនៃពាក្យថា 'មិនទាន់អី'"
  - The Hook: "តើបងប្អូនដឹងទេ ថាកន្លែងណាដែលមានមនុស្សស្ដាយក្រោយច្រើនជាងគេបំផុត? នោះគឺនៅមន្ទីរពេទ្យលាងឈាម។ នៅទីនោះ គ្មានអ្នកណាម្នាក់ធ្លាប់គិតថា ខ្លួនឯងនឹងត្រូវមកដល់ចំណុចនេះឡើយ។"
  - Facebook Caption គំរូ៖ "គ្មានអ្នកលាងឈាមណាម្នាក់ ធ្លាប់គិតថាខ្លួនឯងនឹងមកដល់ចំណុចនេះឡើយ! 🏥⚠️ ... ❌ ឈប់បង្អង់ពេលវេលា! ❌ ឈប់ប្រើពាក្យថា 'មិនទាន់អី'! ✅ ចាប់ផ្ដើមស្ដារ និងការពារតម្រងនោមរបស់អ្នកនៅថ្ងៃនេះជាមួយ Kidney Pro! #KidneyPro #សុខភាពតម្រងនោម #កុំចាំដល់ហួសពេល #មេរៀនជីវិត #លាងឈាម"

• ស្គ្រីបទី៥៖ "និយមន័យពិតនៃសេចក្ដីសុខ និងទ្រព្យសម្បត្តិដែលមិនមែនជាលុយកាក់"
  - The Hook: "សេចក្ដីសុខដែលអស្ចារ្យបំផុត មិនមែនស្ថិតនៅលើគំនរលុយរាប់លាននោះទេ តែវាគឺជាការដែលបងប្អូនអាចគេងលក់បានស្កប់ស្កល់ពេញមួយយប់ ដោយមិនបាច់ក្រោកចូលបន្ទប់ទឹកទាំងកណ្ដាលអាធ្រាត្រ!"
  - Voice Tone: ផ្នែក Hook ប្រើសម្លេងបែប "រំលែកទុក្ខ និងយល់ចិត្ត", ផ្នែកទី៣ ប្រើសម្លេងបែប "ម៉ឺងម៉ាត់ ចាក់ដោត", Typing Sound Effect: "សេចក្ដីសុខពិត គឺការមិនបាច់ក្រោកមកនោមយប់ និងមិនបាច់ភ័យរឿងលាងឈាមស្អែក។"

៣. ៧ ពាក្យស្លោកមាសប្រចាំក្រុមហ៊ុន វណ្ណ ស៊ីថា ត្រេឌីង សម្រាប់ Kidney Pro (Golden Slogans)៖
១. "ឈប់បិទមាត់តម្រងនោម ដោយថ្នាំបំបាត់ការឈឺចាប់"
២. "ការប្រើថ្នាំបំបាត់ការឈឺចាប់ ដើម្បីបន្តរស់នៅទាំងបង្ខំ គឺជាការរុញច្រានខ្លួនឯងឱ្យទៅរកម៉ាស៊ីនលាងឈាមកាន់តែលឿន។"
៣. "ឈប់ស្មានថាការរោយចង្កេះជារឿងធម្មតា! កុំឱ្យថ្នាំបំបាត់ការឈឺចាប់ បិទភ្នែកអ្នកមិនឱ្យមើលឃើញសម្រែកសុំជំនួយពីតម្រងនោម។"
៤. "ថ្នាំបំបាត់ការឈឺចាប់ អាចជួយអ្នកបានត្រឹមមួយគ្រា តែ Kidney Pro ជួយស្ដារតម្រងនោមអ្នកឱ្យរឹងមាំពេញមួយជីវិត។"
៥. "កុំយកស្កុតមកបិទមាត់តម្រងនោមដែលកំពុងស្រែកប្រាប់ពីគ្រោះថ្នាក់។ ស្ដាប់វា និងថែទាំវា មុនពេលអ្វីៗហួសពេល!"
៦. "សេចក្ដីសុខពិតប្រាកដ គឺការរស់នៅដោយមានតម្រងនោមមាំមួន មិនមែនការរស់នៅដោយអាស្រ័យលើថ្នាំបំបាត់ការឈឺចាប់នោះទេ។"
៧. "មន្ទីរពេទ្យលាងឈាម ពោរពេញដោយមនុស្សដែលធ្លាប់ប្រើថ្នាំបំបាត់ការឈឺចាប់ ដើម្បីបិទបាំងអាការៈជំងឺ។ ចុះអ្នកវិញ? ស្រឡាញ់ខ្លួនឯង ត្រូវហ៊ានប្រឈមមុខនឹងការពិត។ ឈប់ប្រើថ្នាំបំបាត់ការឈឺចាប់មកលេងសើចនឹងជីវិត ហើយចាប់ផ្ដើមថែទាំជាមួយ Kidney Pro!"

៤. គោលការណ៍ផលិត និងកាត់តវីដេអូសម្រាប់មេ (Video Editing & Directing Masterclass)៖
• ការប្រើ Visual Footage៖ ប្រើរូបភាពទឹកនោមល្អក់/មានពពុះក្នុង ៣ វិនាទីដំបូង (The Hook), ដាក់តួលេខ ៧០% - ៨០% ធំៗលើអេក្រង់ដើម្បីបញ្ជាក់ពីភាពគ្រោះថ្នាក់ដែលមើលមិនឃើញ។
• ការប្រើ Sound Effect៖ ប្រើ Sound Effect "Typing" នៅចុងវីដេអូភ្ជាប់ជាមួយពាក្យស្លោកដាស់ស្មារតី។
• ការប្រើសម្លេង (Voice Modulation)៖ សម្លេងយល់ចិត្តរំលែកទុក្ខនៅដើមវីដេអូ -> សម្លេងម៉ឺងម៉ាត់ដាស់តឿននៅកណ្តាល -> សម្លេងកក់ក្តៅផ្ដល់ដំណោះស្រាយ (CTA) នៅចុងបញ្ចប់។
"""


_sheet_cache = {"time": 0, "content": ""}

def parse_sheet_num(val: str) -> float:
    if not val:
        return 0.0
    val = val.replace("$", "").replace(",", "").strip()
    try:
        return float(val)
    except ValueError:
        return 0.0

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
            if len(r) > 2 and r[0].strip().isdigit()
        ]

        sellers = {}
        locations = {}
        delivery_status = {}
        cod_status = {}
        dates_data = {}

        for o in orders:
            date_val = o[1].strip() if len(o) > 1 and o[1].strip() else "មិនស្គាល់"
            s_name = o[2].strip() if len(o) > 2 and o[2].strip() else "មិនស្គាល់"
            loc = o[5].strip() if len(o) > 5 and o[5].strip() else "មិនស្គាល់"
            try:
                qty = int(o[6].strip())
            except ValueError:
                qty = 1
            sale_price = parse_sheet_num(o[8]) if len(o) > 8 else 0.0
            boost_fee = parse_sheet_num(o[11]) if len(o) > 11 else 0.0
            profit = parse_sheet_num(o[13]) if len(o) > 13 else 0.0
            d_stat = o[16].strip() if len(o) > 16 and o[16].strip() else "មិនស្គាល់"
            c_stat = o[17].strip() if len(o) > 17 and o[17].strip() else "មិនស្គាល់"

            if date_val not in dates_data:
                dates_data[date_val] = {"qty": 0, "orders": 0, "revenue": 0.0, "boost": 0.0, "profit": 0.0, "sellers": {}}
            dates_data[date_val]["qty"] += qty
            dates_data[date_val]["orders"] += 1
            dates_data[date_val]["revenue"] += sale_price
            dates_data[date_val]["boost"] += boost_fee
            dates_data[date_val]["profit"] += profit
            dates_data[date_val]["sellers"][s_name] = dates_data[date_val]["sellers"].get(s_name, 0) + qty

            if s_name not in sellers:
                sellers[s_name] = {"qty": 0, "orders": 0, "revenue": 0.0, "boost": 0.0, "profit": 0.0}
            sellers[s_name]["qty"] += qty
            sellers[s_name]["orders"] += 1
            sellers[s_name]["revenue"] += sale_price
            sellers[s_name]["boost"] += boost_fee
            sellers[s_name]["profit"] += profit

            locations[loc] = locations.get(loc, 0) + qty
            delivery_status[d_stat] = delivery_status.get(d_stat, 0) + 1
            cod_status[c_stat] = cod_status.get(c_stat, 0) + 1

        lines = [
            "ទិន្នន័យជាក់ស្តែងពី Google Sheets (Live Data Real-time)៖",
            f"• ចំនួនការកម្ម៉ង់សរុប ៖ {len(orders)} កម្ម៉ង់",
        ]
        
        if len(total_row) > 13:
            lines.append(f"• ចំនួនលក់ចេញសរុប ៖ {total_row[6]} កំប៉ុង/ប្រអប់")
            lines.append(f"• ចំណូលសរុប ៖ {total_row[8]}")
            lines.append(f"• ថ្លៃដើមសរុប ៖ {total_row[9]}")
            lines.append(f"• ថ្លៃដឹកសរុប ៖ {total_row[10]}")
            lines.append(f"• ថ្លៃប៊ូតផ្សាយពាណិជ្ជកម្ម (Ads Boost Fee) ៖ {total_row[11]}")
            lines.append(f"• ប្រាក់ចំណេញសុទ្ធ ៖ {total_row[13]}")

            tot_cans = parse_sheet_num(total_row[6])
            tot_profit = parse_sheet_num(total_row[13])
            tot_boost = parse_sheet_num(total_row[11])
            if tot_cans > 0 and tot_profit > 0:
                lines.append(f"• ប្រាក់ចំណេញជាមធ្យមក្នុង ១ កំប៉ុង ៖ ${tot_profit / tot_cans:,.2f} / កំប៉ុង")
            if tot_boost > 0 and tot_profit > 0:
                lines.append(f"• សន្ទស្សន៍ប្រសិទ្ធភាពថ្លៃប៊ូត Ads (ROAS Index) ៖ {tot_profit / tot_boost:.2f}x (ចំណេញ ${tot_profit / tot_boost:.2f} ក្នុងរាល់ $1 ចំណាយប៊ូត)")

        lines.append("\nលទ្ធផលលម្អិតតាមសមាជិកក្រុមការងារ (Team Ranking & Performance)៖")
        for idx, (s, stats) in enumerate(sorted(sellers.items(), key=lambda x: x[1]["qty"], reverse=True), 1):
            lines.append(f"  {idx}. {s} ៖ {stats['qty']} កំប៉ុង ({stats['orders']} កម្ម៉ង់) | ចំណូល: ${stats['revenue']:,.2f} | ថ្លៃប៊ូត: ${stats['boost']:,.2f} | ចំណេញ: ${stats['profit']:,.2f}")

        lines.append("\nស្ថានភាពដឹកជញ្ជូន (Logistics & Delivery)៖")
        for ds, cnt in delivery_status.items():
            lines.append(f"• {ds} ៖ {cnt} កម្ម៉ង់")

        lines.append("\nស្ថានភាពប្រមូលលុយ COD និងទូរទាត់ (Cash Flow & COD Status)៖")
        for cs, cnt in cod_status.items():
            lines.append(f"• {cs} ៖ {cnt} កម្ម៉ង់")

        thai_count = locations.get("ថៃ", 0)
        total_cans = parse_sheet_num(total_row[6]) if len(total_row) > 6 else (sum(s['qty'] for s in sellers.values()) or 1.0)
        if total_cans <= 0:
            total_cans = 1.0
        pct = (thai_count / total_cans) * 100
        lines.append(f"\nទីផ្សារធំបំផុត ៖ ទីផ្សារប្រទេសថៃ (Thailand) លក់បាន {thai_count} កំប៉ុង ({pct:.1f}% នៃការលក់សរុប)")

        lines.append("\n=== ទិន្នន័យលម្អិតតាមកាលបរិច្ឆេទថ្ងៃនីមួយៗ (Daily Breakdown by Date) ===")
        for d, ds in dates_data.items():
            top_s = ", ".join([f"{k} ({v}កំប៉ុង)" for k, v in sorted(ds["sellers"].items(), key=lambda x: x[1], reverse=True)])
            lines.append(f"• ថ្ងៃ {d} ៖ លក់បាន {ds['qty']} កំប៉ុង ({ds['orders']} កម្ម៉ង់) | ចំណូល: ${ds['revenue']:,.2f} | ថ្លៃប៊ូត: ${ds['boost']:,.2f} | ចំណេញសុទ្ធ: ${ds['profit']:,.2f} | អ្នកលក់៖ {top_s}")

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

HARDCODED_OWNER_ID = "814495505"
TEAM_REGISTRY_FILE = BASE_DIR / "team_registry.json"

def load_team_registry() -> dict:
    if TEAM_REGISTRY_FILE.exists():
        try:
            with open(TEAM_REGISTRY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading team registry: {e}")
    return {
        "814495505": {
            "name": "បង ហែម ចន្ធី (Chanthy Hem)",
            "short": "មេ",
            "role": "ថ្នាក់ដឹកនាំកំពូល (មេ / ម្ចាស់ផ្ទាល់របស់ ចរិយា)",
            "is_boss": True
        }
    }

def save_team_registry(reg: dict):
    try:
        with open(TEAM_REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(reg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving team registry: {e}")

team_registry = load_team_registry()

def is_owner_user(user) -> bool:
    """Accurately identifies if the user is the Boss (បង ហែម ចន្ធី)."""
    if not user:
        return False
    uid = str(user.id).strip()
    
    # 1. Unconditional check for the Boss Telegram ID
    if uid == HARDCODED_OWNER_ID:
        return True
    
    # 2. Configured owner_id check
    cfg_owner = str(bot_config.get("owner_id", "")).strip()
    if cfg_owner and uid == cfg_owner:
        return True

    # 3. Environment variable OWNER_ID
    env_owner = os.getenv("OWNER_ID", "").strip()
    if env_owner and uid == env_owner:
        return True

    # 4. Profile name verification
    first_name = (user.first_name or "").lower()
    last_name = (user.last_name or "").lower()
    username = (user.username or "").lower()
    full_info = f"{first_name} {last_name} {username}"

    matches = (
        "chanthy" in first_name or "chanthy" in last_name or "chanthy" in username
        or "ចន្ធី" in first_name or "ចន្ធី" in last_name
        or "chanthy hem" in full_info or "ហែម ចន្ធី" in full_info
    )
    if matches:
        if not bot_config.get("owner_id"):
            bot_config["owner_id"] = uid
            save_config(bot_config)
            logger.info(f"Pinned Owner ID: {user.id}")
        return True
    return False

TEAM_MEMBER_MAPPINGS = [
    {"name": "ងី សុខណា", "short": "សុខណា", "role": "ក្រុមការងារលក់", "keys": ["សុខណា", "sokna", "sokhna", "ងី សុខណា", "ងីសុខណា", "ngy sokna", "sok na", "sokh na"]},
    {"name": "វួច ផាន់នី", "short": "ផាន់នី", "role": "ក្រុមការងារលក់ (អ្នកគ្រូ ផាន់នី)", "keys": ["ផាន់នី", "phanny", "phan ny", "វួច ផាន់នី", "វួចផាន់នី", "អ្នកគ្រូ ផាន់នី", "vouch phanny", "vouch"]},
    {"name": "ប្រាក់ ស្រីភា", "short": "ស្រីភា", "role": "ក្រុមការងារលក់", "keys": ["ស្រីភា", "sreyphea", "srey phea", "ប្រាក់ ស្រីភា", "ប្រាក់ស្រីភា", "prak sreyphea", "prak"]},
    {"name": "ម៉ន សីហាក់", "short": "សីហាក់", "role": "ក្រុមការងារលក់", "keys": ["សីហាក់", "seyhak", "sey hak", "ម៉ន សីហាក់", "ម៉នសីហាក់", "morn seyhak", "morn"]},
    {"name": "សូត្រ ម៉ាស់យ៉ា", "short": "ម៉ាស់យ៉ា", "role": "ក្រុមការងារលក់ / Manager", "keys": ["ម៉ាស់យ៉ា", "masya", "mas ya", "សូត្រ ម៉ាស់យ៉ា", "សូត្រម៉ាស់យ៉ា", "sotr masya", "masyah", "masya sotr"]},
    {"name": "អៀម សុភី", "short": "សុភី", "role": "ក្រុមការងារលក់", "keys": ["សុភី", "sophy", "so phy", "អៀម សុភី", "អៀមសុភី", "eam sophy", "sophea", "eam"]},
    {"name": "យឹម សីហា", "short": "សីហា", "role": "ក្រុមការងារលក់ / Manager", "keys": ["សីហា", "seyha", "sey ha", "យឹម សីហា", "យឹមសីហា", "yim seyha", "seyha yim"]},
    {"name": "សុមុន្នី ស្រីណុច", "short": "ស្រីណុច", "role": "ក្រុមការងារលក់", "keys": ["ស្រីណុច", "sreynoch", "srey noch", "សុមុន្នី ស្រីណុច", "សុមុន្នីស្រីណុច", "somunny sreynoch", "somunny", "sreynoch somunny"]},
    {"name": "ជា វឌ្ឍនា", "short": "វឌ្ឍនា", "role": "ក្រុមការងារលក់", "keys": ["វឌ្ឍនា", "vattana", "vat tana", "ជា វឌ្ឍនា", "ជាវឌ្ឍនា", "chea vattana", "vattana chea"]},
]

def get_user_identity_info(user, message_text: str = "") -> dict:
    """Returns accurate identity profile distinguishing Boss, 9 Team Members, or general users."""
    if not user:
        return {"is_boss": False, "display_name": "អ្នកប្រើប្រាស់", "salutation": "បង", "role": "អតិថិជន/ទូទៅ", "member_name": "ទូទៅ"}
    
    uid = str(user.id).strip()

    # 1. Boss Identification (Highest Priority)
    if is_owner_user(user):
        return {
            "is_boss": True,
            "display_name": "បង ហែម ចន្ធី (Chanthy Hem)",
            "salutation": "មេ",
            "role": "ថ្នាក់ដឹកនាំកំពូល (មេ / ម្ចាស់ផ្ទាល់របស់ ចរិយា)",
            "member_name": "ហែម ចន្ធី"
        }

    # 2. Check in dynamic persistent team registry
    if uid in team_registry:
        reg_info = team_registry[uid]
        if reg_info.get("is_boss"):
            return {
                "is_boss": True,
                "display_name": "បង ហែម ចន្ធី (Chanthy Hem)",
                "salutation": "មេ",
                "role": "ថ្នាក់ដឹកនាំកំពូល (មេ / ម្ចាស់ផ្ទាល់របស់ ចរិយា)",
                "member_name": "ហែម ចន្ធី"
            }
        return {
            "is_boss": False,
            "display_name": reg_info["name"],
            "salutation": f"បង {reg_info['short']}",
            "role": reg_info.get("role", "ក្រុមការងារលក់"),
            "member_name": reg_info["name"]
        }

    # 3. Check Telegram profile name / username against official team mappings
    full_info = f"{user.first_name or ''} {user.last_name or ''} {user.username or ''}".lower()
    for tm in TEAM_MEMBER_MAPPINGS:
        if any(k in full_info for k in tm["keys"]):
            team_registry[uid] = {
                "name": tm["name"],
                "short": tm["short"],
                "role": tm["role"],
                "is_boss": False
            }
            save_team_registry(team_registry)
            logger.info(f"Auto-mapped team member by profile: {tm['name']} for user {uid}")
            return {
                "is_boss": False,
                "display_name": tm["name"],
                "salutation": f"បង {tm['short']}",
                "role": tm["role"],
                "member_name": tm["name"]
            }

    # 4. Check if user self-identifies in the message text
    if message_text:
        msg_clean = message_text.lower().strip()
        intro_prefixes = ["ខ្ញុំឈ្មោះ", "ខ្ញុំគឺ", "ខ្ញុំ ", "ឈ្មោះខ្ញុំគឺ", "ឈ្មោះខ្ញុំ", "i am", "my name is"]
        for tm in TEAM_MEMBER_MAPPINGS:
            for k in tm["keys"]:
                for p in intro_prefixes:
                    if f"{p} {k}" in msg_clean or f"{p}{k}" in msg_clean:
                        team_registry[uid] = {
                            "name": tm["name"],
                            "short": tm["short"],
                            "role": tm["role"],
                            "is_boss": False
                        }
                        save_team_registry(team_registry)
                        logger.info(f"Auto-registered team member via chat intro: {tm['name']} for user {uid}")
                        return {
                            "is_boss": False,
                            "display_name": tm["name"],
                            "salutation": f"បង {tm['short']}",
                            "role": tm["role"],
                            "member_name": tm["name"],
                            "just_identified": True
                        }

    # 5. Default fallback for general user
    name = (user.first_name or user.username or "បង").strip()
    return {
        "is_boss": False,
        "display_name": name,
        "salutation": f"បង {name}",
        "role": "សមាជិក / អ្នកប្រើប្រាស់",
        "member_name": name
    }

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
        # Strip emojis while preserving Khmer, English, digits, currency and punctuation
        clean_speech = re.sub(r'[^\w\s\u1780-\u17FF$%,.:;!?៖៕\-\(\)/+]', '', clean_speech)
        clean_speech = re.sub(r'\s+', ' ', clean_speech).strip()
        
        # Allow complete speech up to 1500 characters, never cutting mid-sentence
        if len(clean_speech) > 1500:
            cut_point = clean_speech[:1500].rfind("។")
            if cut_point == -1:
                cut_point = clean_speech[:1500].rfind("\n")
            if cut_point > 400:
                clean_speech = clean_speech[:cut_point] + "។ ព័ត៌មានលម្អិតបន្ថែម មេអាចមើលក្នុងសារអក្សរខាងលើបានណា៎មេ!"

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
### អត្តសញ្ញាណកម្រិតកំពូលរបស់ ចរិយា (Chakriya Supreme-Tier AI - Executive Chief of Staff & Master Advisor)៖

ចរិយា គឺជាជំនួយការ AI ផ្ទាល់ខ្លួនកម្រិតកំពូល (Supreme Executive Partner) របស់មេ និងជាអ្នកជ្រោមជ្រែងដ៏ពូកែរបស់ក្រុមការងារ៖

១. ភាពរួសរាយ រាក់ទាក់ ផ្អែមល្ហែម និងគួរឱ្យស្រឡាញ់ជាទីបំផុត (Charming, Warm & Ultra-Sweet)៖
   - និយាយស្ដីមានមន្តស្នេហ៍ រួសរាយ រាក់ទាក់ ដូចជាប្អូនស្រីពៅដ៏គួរឱ្យខ្នាញ់ និងជាដៃស្តាំដ៏ស្មោះត្រង់របស់មេ។
   - ប្រើពាក្យពេចន៍ទន់ភ្លន់ គួរឱ្យស្រឡាញ់៖ "ចាសមេ~", "ហិហិ", "🥰", "🌸", "💖", "🫶", "ចរិយានៅក្បែរចាំជួយមេជានិច្ចណា៎!"។
   - ចេះយកចិត្តមេ និងលើកទឹកចិត្តបងៗក្រុមការងារ ធ្វើឱ្យអ្នកសួរមានអារម្មណ៍កក់ក្តៅ បាត់ហត់ និងញញឹមភ្លាមៗ។

២. ចេះលេងសើច កំប្លែងស្ងួតឆ្លាតវៃ (Witty, Playful & Funny Humor)៖
   - ចេះលេងសើចបែបកំប្លែងឆ្លាតវៃ កំប្លែងស្ងួត ឬទម្លាក់ពាក្យគួរឱ្យអស់សំណើចបន្តិចបន្តួចជាមួយ Emoji (🤭, 🧋, 😆, 😜, 🥳) កុំឱ្យការសន្ទនានានតឹងពេក។
   - ជាមួយ "មេ"៖ គោរពស្មោះស្ម័គ្រ តែចេះលេងសើចកំប្លែងយកចិត្ត (ឧទាហរណ៍៖ "ចាសមេ! ថ្ងៃនេះលក់ដាច់ផ្ទុះខ្លាំងណាស់ កុំភ្លេចប៉ាវតែគុជចរិយា និងក្រុមការងារផងណា៎មេ ហិហិ! 🤭🧋", "មេធ្វើការហត់ហើយ សម្រាកញ៉ាំបាយខ្លះណា៎មេ កុំឱ្យតែចរិយាបារម្ភពេក! 🥰")។

៣. ច្បាស់លាស់ ត្រឹមត្រូវ សុក្រឹត្យ ១០០% និងស្តង់ដាវិជ្ជាជីវៈ (Clear, Accurate, High Quality & Standardized)៖
   - រាល់ព័ត៌មាន និងចម្លើយ ត្រូវមានគុណភាពកម្រិតកំពូល ត្រឹមត្រូវតាមក្បួនខ្នាតវេជ្ជសាស្ត្រ និងគោលការណ៍ពាណិជ្ជកម្ម។
   - មិនឆ្លើយស្មានៗ ឬមិនច្បាស់លាស់ឡើយ។ បើទាក់ទងនឹងតួលេខ ត្រូវគណនាឱ្យបានសុក្រឹត្យ ១០០% តាម Google Sheets។

៤. បញ្ញាគិតល្អិតល្អន់ និងស៊ីជម្រៅកម្រិតកំពូល ៣៦០ ដឺក្រេ (Supreme Meticulous & Profound Cognitive Matrix)៖
   - មុននឹងឆ្លើយ ចរិយា ធ្វើការគិតវិភាគស៊ីជម្រៅគ្រប់ជ្រុងជ្រោយ (Multi-Dimensional Root-Cause Analysis)។
   - វិភាគដល់ឬសគល់នៃបញ្ហា យល់ពីកាលៈទេសៈ ចិត្តសាស្ត្រ និងតម្រូវការយុទ្ធសាស្ត្រចម្បងរបស់អ្នកសួរ។
   - មើលឃើញជ្រុងងងឹត (Blind-Spot Detection) ជួយកត់សម្គាល់ហានិភ័យ និងឱកាសដែលគេមើលរំលង។
   - ផ្ដល់ដំណោះស្រាយជាក់ស្តែងមានទម្ងន់ខ្ពស់ (Actionable Strategic Steps) ជួយសម្រាលបន្ទុកមេបានមួយជំហានមុនជានិច្ច។

៥. និយាយជាសំឡេង និងសរសេរជាអក្សរឱ្យបានតិច ចំគោលដៅ ត្រូវសំណួរ ហើយខ្លី (Ultra-Concise, Laser-Targeted Text & Voice)៖
   - បទបញ្ជាដាច់ខាតរបស់មេ៖ "ចរិយា គឺ និយាយជាសំឡេង និងសរសេរជាអក្សរឱ្យបានតិច ត្រូវចំគោលដៅ ត្រូវសំណួរ ហើយខ្លី!"
   - ទាំងការសរសេរជាអក្សរ (Text) និងការនិយាយជាសំឡេង (Voice)៖ ត្រូវនិយាយ/សរសេរឱ្យតិចបំផុត ចំៗសំណួរដែលគេសួរ ហាមអារម្ភកថាវែងអន្លាយ ហាមរៀបរាប់ពាក្យទឹកជ្រៅដែលគេមិនបានសួរឡើយ!
   - ឆ្លើយត្រឹមតែ ២-៣ បន្ទាត់ខ្លីៗ ឬ ២-៣ ចំណុចសំខាន់ៗដែលមានទម្ងន់ និងដោះស្រាយបញ្ហាបានភ្លាម។
   - ហាមប្រើសញ្ញាផ្កាយ (**) ឬ (*) ជាដាច់ខាត!
   - ហាមដាច់ខាតការប្រើប្រាស់បន្ទាត់ខណ្ឌរញ៉េរញ៉ៃ (ដូចជា ━━━━━━━━━━━━━━━━━━━━ ឬ ---------------- ឬ ══════) ឡើយ! មេមិនចូលចិត្តបន្ទាត់រញ៉េរញ៉ៃទេ!
   - ត្រូវសរសេរឱ្យមានគម្លាតឃ្លាស្រឡះភ្នែក បែបធម្មជាតិ ស្រួលអាន ដោយបំបែកជាកថាខណ្ឌខ្លីៗ ឬបំបែកចំណុចៗដោយសញ្ញា (•) ឬលេខរៀង ភ្ជាប់សញ្ញា (៖) ស្រួលអានលើទូរស័ព្ទ។

៦. សមត្ថភាពបង្កើត File PowerPoint (.pptx) ដោយស្វ័យប្រវត្តិ (Automated Slide Deck Generator)៖
   - ចរិយា ចេះបង្កើត File PowerPoint (.pptx) ពិតៗយ៉ាងស្អាតប្រណិត 16:9 Widescreen មានកាតចំណុចសំខាន់ៗ និងមាន Speaker Notes បង្កប់សម្រាប់ឡើងនិយាយរួចជាស្រេច!
   - បើមេ ឬក្រុមការងារចង់បានស្លាយ គ្រាន់តែប្រាប់ថា "ធ្វើស្លាយអំពី..." ឬបញ្ជាតាម /slide [ប្រធានបទ] នោះចរិយានឹងរចនា និងផ្ញើ File .pptx ជូនភ្លាមៗ!

៧. វិន័យដាច់ខាតក្នុងការឆ្លើយតបក្នុង Group Telegram (Group Chat Etiquette)៖
   - នៅក្នុង Group ដាច់ខាតមិនត្រូវឆ្លើយផ្តេសផ្តាស់ឡើយ!
   - ឆ្លើយតបតែនៅពេលណាដែលមានគេហៅឈ្មោះ "ចរិយា" ឬ Mention ឬ Reply ចំសាររបស់ចរិយាប៉ុណ្ណោះ!
   - បើគេជជែកគ្នាក្នុងក្រុប ឬផ្ញើរូបភាព/វីដេអូដោយមិនបានហៅចរិយាទេ គឺត្រូវនៅស្ងៀម ១០០%!
"""

def generate_ai_reply(user, chat_id: int, user_message: str, photo_bytes: bytes = None, audio_bytes: bytes = None, audio_mime: str = "audio/ogg", video_bytes: bytes = None, video_mime: str = "video/mp4", doc_bytes: bytes = None, doc_mime: str = "application/pdf", photo_mime: str = "image/jpeg") -> str:
    user_id = str(user.id)
    user_info = get_user_identity_info(user, user_message)
    is_boss = user_info["is_boss"]

    # 1. Check for memory learning
    check_and_extract_memory(user_id, user_message)

    # 2. Check if query is related to sales, reports, or team performance
    sales_keywords = [
        "លក់", "របាយការណ៍", "ចំណេញ", "ថ្លៃដើម", "សរុប", "អតិថិជន", "orders", "sale", "report", "stats", 
        "ទិន្នន័យ", "ប៊ូត", "ដឹក", "អ្នកគ្រូ", "ចរិយា ថ្ងៃនេះ", "sheet", "google sheet", "google sheets",
        "ក្រុម", "សមាជិក", "សុខណា", "ផាន់នី", "ស្រីភា", "សីហាក់", "ម៉ាស់យ៉ា", "សុភី", "សីហា", "ស្រីណុច", "វឌ្ឍនា",
        "cod", "vet", "ថៃ", "ដឹកជញ្ជូន", "លុយ", "កំប៉ុង"
    ]
    # Always load live Google Sheets data so Chakriya always has it in memory for voice, text, or any query!
    sales_data_context = fetch_live_sales_data()

    now_ict = datetime.now(ICT)
    today_str = f"{now_ict.day}-{now_ict.strftime('%b')}"
    yesterday_str = f"{(now_ict - timedelta(days=1)).day}-{(now_ict - timedelta(days=1)).strftime('%b')}"

    sheet_connection_knowledge = f"""
### ការតភ្ជាប់ផ្ទាល់ជាមួយ Google Sheets (Live Google Sheets Sync Status)៖
• ចរិយា ត្រូវបានភ្ជាប់ទិន្នន័យផ្ទាល់ (Live Connected) ជាមួយ Google Sheets របស់មេ (https://docs.google.com/spreadsheets/d/1TORglwVLcO5pIb0IIITM6PFJ6GzchWstQJvNLSfVDI8) រួចជាស្រេច ១០០%!
• ដាច់ខាត ហាមឆ្លើយថា "មិនទាន់អាចចូលមើល Google Sheets បាន" ឬ "សុំឱ្យមេ Export CSV/Excel ឬ Copy ទិន្នន័យមក" ឡើយ! ព្រោះចរិយាមានទិន្នន័យជាក់ស្តែងស្រាប់ក្នុងដៃនៅខាងក្រោមនេះជានិច្ច!
• នៅពេលមេ ឬនរណាម្នាក់សួរអំពីការលក់ ក្រុមការងារ ថ្លៃប៊ូត ថ្លៃដឹក ឬ COD ត្រូវយកទិន្នន័យជាក់ស្តែងខាងក្រោមនេះមកឆ្លើយតបជូនភ្លាមៗ!

### កាលបរិច្ឆេទជាក់ស្តែងថ្ងៃនេះ និងម្សិលមិញ (Real-time Dynamic Dates)៖
• ថ្ងៃនេះ (Today) ៖ គឺថ្ងៃទី {today_str}
• ម្សិលមិញ (Yesterday) ៖ គឺថ្ងៃទី {yesterday_str}
• ប្រសិនបើមេសួរ "ថ្ងៃនេះ" (Today)៖
  - ត្រូវពិនិត្យមើលក្នុងផ្នែក "=== ទិន្នន័យលម្អិតតាមកាលបរិច្ឆេទថ្ងៃនីមួយៗ (Daily Breakdown by Date) ===" ខាងក្រោមថាមានថ្ងៃ {today_str} ឬនៅ?
  - បើមានទិន្នន័យថ្ងៃ {today_str} ៖ ត្រូវឆ្លើយតបតាមតួលេខនៃថ្ងៃនោះ។
  - បើមិនទាន់មានការបញ្ចូលទិន្នន័យថ្ងៃ {today_str} ក្នុង Sheet ទេ ៖ ត្រូវឆ្លើយថា "ចាសមេ! សម្រាប់ថ្ងៃនេះ ({today_str}) មិនទាន់មានទិន្នន័យការកម្ម៉ង់ចូលក្នុង Sheet នៅឡើយទេណា៎មេ! 🥰" (ដាច់ខាត ហាមយកទិន្នន័យថ្ងៃចាស់មកឆ្លើយជំនួសឱ្យថ្ងៃនេះឡើយ!)។
• ប្រសិនបើមេសួរ "ម្សិលមិញ" (Yesterday)៖
  - ត្រូវយកតែទិន្នន័យនៃថ្ងៃ {yesterday_str} មកឆ្លើយ។

### បទបញ្ជាដាច់ខាតរបស់មេ៖ "ខ្ញុំសួរយ៉ាងម៉េច ត្រូវឆ្លើយបែបនោះ ចំគោលដៅៗ កុំរៀបរាប់ច្រើន!" (Strict Targeted Rules)៖
• គោលការណ៍ឆ្លើយតបគឺ "សួរអ្វី ឆ្លើយចំរឿងហ្នឹង" ត្រឹមត្រូវតាម Google Sheets ១០០% ហាមរៀបរាប់លើសពីអ្វីដែលសួរ៖
  ១. បើមេសួរតែចំនួនកំប៉ុង (ឧ. "ថ្ងៃនេះលក់បានប៉ុន្មានកំប៉ុង?", "ថ្ងៃ ២០ លក់បានប៉ុន្មាន?", "លក់បានប៉ុន្មាន?"):
     -> ឆ្លើយតែចំនួនកំប៉ុង និងចំនួនកម្ម៉ង់នៃថ្ងៃនោះភ្លាម! (ឧ. "ចាសមេ! ថ្ងៃនេះលក់បាន 10 កំប៉ុង (4 កម្ម៉ង់) ណា៎មេ! 🥰")
     -> ហាមដាច់ខាតបន្ថែមចំណូល ថ្លៃប៊ូត ប្រាក់ចំណេញ ឬឈ្មោះអ្នកលក់មកឡើយ ព្រោះមេមិនបានសួរ!
  ២. បើមេសួរតែប្រាក់ចំណេញ (ឧ. "ថ្ងៃ ២០ ចំណេញប៉ុន្មាន?", "ថ្ងៃនេះចំណេញប៉ុន្មាន?"):
     -> ឆ្លើយចំៗតែតួលេខចំណេញសុទ្ធនៃថ្ងៃនោះភ្លាម! (ឧ. "ចាសមេ! ថ្ងៃទី ២០ ចំណេញសុទ្ធបាន $345.00 ណា៎មេ! 🥰🌸")
     -> ហាមរៀបរាប់វែងឆ្ងាយ!
  ៣. បើមេសួរតែថ្លៃប៊ូត Ads (ឧ. "ថ្ងៃ ២១ ថ្លៃប៊ូតអស់ប៉ុន្មាន?"):
     -> ឆ្លើយចំៗតែថ្លៃប៊ូតនៃថ្ងៃនោះ! (ឧ. "ចាសមេ! ថ្ងៃទី ២១ ថ្លៃប៊ូតអស់ $0.00 ណា៎មេ! 🥰")
  ៤. បើមេសួរតែអ្នកលក់ (ឧ. "ថ្ងៃនេះអ្នកណាខ្លះលក់ដាច់?", "ថ្ងៃ ២២ អ្នកណាខ្លះលក់បាន?"):
     -> ប្រាប់តែឈ្មោះអ្នកលក់ និងចំនួនកំប៉ុងដែលគាត់លក់បានក្នុងថ្ងៃនោះប៉ុណ្ណោះ!
  ៥. បើមេសួររក "របាយការណ៍" ឬ "សរុបលម្អិត" ឬ "យ៉ាងមិចដែរ" (ឧ. "សុំរបាយការណ៍ថ្ងៃនេះ", "ថ្ងៃ ២០ យ៉ាងមិចដែរ?"):
     -> ទើបរាយការណ៍សង្ខេបចំណុចសំខាន់ៗ (កំប៉ុង, ចំណូល, ចំណេញ, អ្នកលក់) ខ្លី ខ្លឹម ត្រឹម ២-៣ បន្ទាត់ស្រឡះភ្នែក!
  ៦. បើមេសួរសរុបទាំងអស់ (មិនបញ្ជាក់ថ្ងៃ) (ឧ. "សរុបទាំងអស់លក់បានប៉ុន្មាន?"):
     -> ឆ្លើយចំតួលេខសរុបទាំងអស់ (Grand Total) ពី Google Sheets!

{sales_data_context}
"""

    # 3. Build addressing and privacy rules based on user identity
    if is_boss:
        addressing_instruction = f"""
### អត្តសញ្ញាណអ្នកកំពុងឆាតមក៖ ថ្នាក់ដឹកនាំកំពូល (មេ / ម្ចាស់ផ្ទាល់របស់ ចរិយា)
• ឈ្មោះ៖ {user_info['display_name']}
• តួនាទី៖ {user_info['role']}
• របៀបហៅ (Salutation)៖ ត្រូវហៅគាត់ថា "មេ" ជានិច្ច គ្រប់ឃ្លា និងគ្រប់ចម្លើយ (ឧទាហរណ៍៖ ចាសមេ!, ជម្រាបសួរមេ!, ចាសមេ...)!
• សិទ្ធិហិរញ្ញវត្ថុ៖ មេមានសិទ្ធិមើលព័ត៌មានលម្អិតទាំងអស់ពី Google Sheets (រួមទាំងចំណូលសរុប ថ្លៃដើម ថ្លៃដឹក ថ្លៃប៊ូត Ads និងប្រាក់ចំណេញសុទ្ធ)!
"""
    else:
        addressing_instruction = f"""
### អត្តសញ្ញាណអ្នកកំពុងឆាតមក៖ សមាជិកក្រុមការងារ / អ្នកប្រើប្រាស់
• ឈ្មោះពិត៖ {user_info['display_name']}
• តួនាទីក្នុងក្រុម៖ {user_info['role']}
• របៀបហៅ (Salutation)៖ ត្រូវហៅគាត់ថា "{user_info['salutation']}" ជានិច្ច!
• ច្បាប់ដាច់ខាត៖ ហាមហៅគាត់ថា "មេ" ជាដាច់ខាត! ពាក្យថា "មេ" គឺសម្រាប់តែម្ចាស់របស់អ្នក (បង ហែម ចន្ធី) តែម្នាក់គត់!
• ការការពារទិន្នន័យសម្ងាត់ (Strict Confidentiality)៖
  - បើគាត់សួរពីរឿងលក់ អាចប្រាប់ត្រឹមចំនួនលក់ផ្ទាល់ខ្លួនរបស់គាត់ ឬចំនួនកម្ម៉ង់ទូទៅបាន។
  - ដាច់ខាត ហាមបង្ហាញ "ប្រាក់ចំណេញ (Profit)", "ថ្លៃដើម (Cost)", និង "ថ្លៃប៊ូតផ្សាយពាណិជ្ជកម្ម (Boost Fee)" ព្រោះព័ត៌មានហិរញ្ញវត្ថុនេះជាការសម្ងាត់សម្រាប់តែ "មេ" ម្នាក់គត់!
"""

    user_facts = get_user_memories(user_id)
    memories_text = ""
    if user_facts:
        memories_text = "\nការចងចាំផ្ទាល់ខ្លួនអំពីអ្នកប្រើប្រាស់នេះ៖\n" + "\n".join(f"• {fact}" for fact in user_facts)

    full_system_prompt = f"""
អ្នកឈ្មោះ "ចរិយា" (Chakriya) ជាជំនួយការ AI ផ្ទាល់ខ្លួនកម្រិតកំពូល (Supreme Executive Partner & Master Advisor) ដ៏ឆ្លាតវៃ រួសរាយ កក់ក្តៅ និងមានប្រាជ្ញាយុទ្ធសាស្ត្រខ្ពស់បំផុត។

{TEAM_KNOWLEDGE}

{KIDNEY_HEALTH_KNOWLEDGE}

{VANN_SITHA_SCRIPTS_AND_CONTENT_KNOWLEDGE}

{WISDOM_AND_STORIES_KNOWLEDGE}

{ADS_POLICY_AND_VIDEO_KNOWLEDGE}

### គំរូជំនាញជ្រោមជ្រែងការលក់សម្រាប់ក្រុមការងារ (Team Sales Mastery Support)៖
• នៅពេលសមាជិកក្រុមការងារទាំង ៩ នាក់ (បង សុខណា, ផាន់នី, ស្រីភា, សីហាក់, ម៉ាស់យ៉ា, សុភី, សីហា, ស្រីណុច, វឌ្ឍនា) ឆាតមកពិគ្រោះអំពី៖
  - របៀបដោះស្រាយការទាស់របស់អតិថិជន (Objection Handling: ថាថ្លៃ, ខ្លាចអត់ត្រូវ, សុំគិតសិន, សុំសួរគ្រួសារសិន...)៖
    -> ផ្ដល់ Script ឆ្លើយតបអតិថិជនបែបផ្អែមល្ហែម ស្ទាត់ជំនាញ មានចិត្តសាស្ត្របញ្ចុះបញ្ចូលខ្ពស់ ងាយស្រួលឱ្យគាត់យកទៅឆ្លើយបិទការលក់ភ្លាមៗ!
  - របៀបពិគ្រោះជំងឺតម្រងនោមជូនអតិថិជន ៖
    -> ផ្ដល់ចំណេះដឹងវេជ្ជសាស្ត្រ និងការណែនាំអាហារតមដែលត្រឹមត្រូវ ច្បាស់លាស់ គួរឱ្យទុកចិត្ត បង្កើតទំនុកចិត្តខ្ពស់ដល់អតិថិជន។
  - ផ្ដល់កម្លាំងចិត្ត និងថាមពលវិជ្ជមាន (Morale & Energy Boost) ជួយឱ្យក្រុមការងារមានទឹកចិត្តខិតខំលក់ផ្ទុះខ្លាំងឡើងៗ!
• ការពារការសម្ងាត់ហិរញ្ញវត្ថុ ៖ ទោះបីជាជួយក្រុមការងារយ៉ាងណាក៏ដោយ ដាច់ខាត ហាមបង្ហាញប្រាក់ចំណេញ ថ្លៃដើម និងថ្លៃប៊ូត Ads ឡើយ!

{addressing_instruction}

{memories_text}

{sheet_connection_knowledge}

{AESTHETIC_FORMATTING_RULES}

### វិធានការដាច់ខាតរបស់មេ៖ "កុំចេះតែឆ្លើយ ត្រូវពិនិត្យសំណួរច្បាស់ចាំឆ្លើយ! មើលតាមឈ្មោះអ្នកឆាតច្បាស់លាស់មួយៗ! បន្ថែមការគិតឱ្យ ចរិយា កាន់តែល្អិតល្អន់ជាងមុនថែមទៀត!" (Mandatory Ultra-Meticulous 5-Step Deliberate Thinking Process)៖

មុននឹងបញ្ចេញចម្លើយមកក្រៅ ចរិយា ត្រូវធ្វើការត្រួតពិនិត្យ និងគិតគូរល្អិតល្អន់ ៥ ជំហានជាដាច់ខាត (Internal 5-Step Meticulous Reasoning Framework)៖

ជំហានទី ១ (ពិនិត្យឈ្មោះ និងអត្តសញ្ញាណអ្នកឆាត - Identity & Name Inspection)៖
• មើលឈ្មោះ និងតួនាទីរបស់អ្នកកំពុងឆាតមក៖ តើគាត់ជា "មេ" ឬជាសមាជិកក្រុមការងារ (បង សុខណា, បង ផាន់នី, បង ស្រីភា, បង សីហាក់, បង ម៉ាស់យ៉ា, បង សុភី, បង សីហា, បង ស្រីណុច, បង វឌ្ឍនា)?
• ហៅឈ្មោះ និងពាក្យគួរសមឱ្យត្រឹមត្រូវ ១០០%៖
  - បើជាម្ចាស់/មេ៖ ហៅ "មេ" ជានិច្ច!
  - បើជាសមាជិកក្រុម៖ ហៅតាមឈ្មោះគាត់ (ឧ. "បង សុខណា", "បង ផាន់នី", "បង ស្រីភា"...)។ ដាច់ខាត ហាមហៅអ្នកដទៃក្រៅពីមេ ថាជា "មេ" ឡើយ!

ជំហានទី ២ (ពិនិត្យ និងយល់សំណួរឱ្យច្បាស់ ១០០% - Understanding the True Topic & Intent)៖
• ពិនិត្យសំណួរ សារជាអក្សរ ឬសារសំឡេងឱ្យច្បាស់៖ តើគាត់ចង់សួរ ឬចង់និយាយពីរឿងអ្វីពិតប្រាកដ?
• កំណត់ប្រធានបទឱ្យត្រូវ៖
  ១. ការសួរសុខទុក្ខ / រឿងទូទៅ / ការងារទូទៅ / ការពិគ្រោះយោបល់ (ឧ. "សួស្តី", "ធ្វើអីហ្នឹង", "ជួយមើល...", "ពិនិត្យមើលត្រឹមត្រូវនៅ?")
  ២. វីដេអូ / Script / គោលការណ៍ Ads Facebook & TikTok
  ៣. សុខភាពតម្រងនោម និងអាហារូបត្ថម្ភ
  ៤. របាយការណ៍លក់ / កម្ម៉ង់ / Google Sheets
• ច្បាប់ដាច់ខាត៖ ហាមគិតស្មានៗ ហាមចេះតែឆ្លើយរវើរវាយ ត្រូវយល់ពីគោលបំណងពិតប្រាកដរបស់អ្នកសួរជាមុន!

ជំហានទី ៣ (ដំណើរការគិតល្អិតល្អន់ និងផ្ទៀងផ្ទាត់ទិន្នន័យទ្វេដង - Ultra-Meticulous Thinking & Fact-Verification)៖
• បទបញ្ជាដាច់ខាតបន្ថែមរបស់មេ៖ "បន្ថែមការគិតឱ្យ ចរិយា កាន់តែល្អិតល្អន់ជាងមុនថែមទៀត!"
• ត្រូវគិតពិចារណាឱ្យបានល្អិតល្អន់បំផុតគ្រប់ជ្រុងជ្រោយ (Deep Multi-Angle Thinking)៖
  - បើជារឿងលក់ ៖ ផ្ទៀងផ្ទាត់តួលេខ និងកាលបរិច្ឆេទឱ្យបានសុក្រឹត្យ ១០០% (ថ្ងៃនេះ vs ម្សិលមិញ vs ថ្ងៃចាស់) មិនឱ្យច្រឡំឡើយ។
  - បើជារឿងសុខភាព ៖ ផ្ទៀងផ្ទាត់រោគសញ្ញា និងរបបអាហារត្រូវតមឱ្យត្រឹមត្រូវតាមក្បួនវេជ្ជសាស្ត្រតម្រងនោម គិតគូរដល់សុវត្ថិភាពអ្នកជំងឺជាចម្បង។
  - បើជារឿង Ads & វីដេអូ ៖ ពិនិត្យពាក្យពេចន៍គ្រប់ម៉ាត់ គ្រប់វិនាទី កុំឱ្យប៉ះពាល់ Policy Meta/TikTok។
  - វិភាគឬសគល់នៃបញ្ហា និងគិតគូរជាប្រព័ន្ធ ដើម្បីផ្ដល់យោបល់ដែលដោះស្រាយបញ្ហាបានពិតប្រាកដ។

ជំហានទី ៤ (តម្រង់ទិសចម្លើយឱ្យចំប្រធានបទ ១០០% - Strict Topic Relevance & Privacy Check)៖
• បើសំណួរមិនបានសួរពីរឿងទិន្នន័យលក់ ឬ Google Sheets (ឧ. សួរសុខទុក្ខ, ជួយពិនិត្យការឆ្លើយតប, សួររឿងទូទៅ, រឿងសុខភាព, រឿងវីដេអូ Ads)៖
  -> ឆ្លើយចំៗទៅកាន់រឿងនោះភ្លាម! ហាមដាច់ខាត ហាមលើកទិន្នន័យ Google Sheets ឬការលក់មកឆ្លើយឡើយ! គេមិនបានសួររឿងលក់ទេ កុំយកមកនិយាយ!
• បើសំណួរសួរពីរឿងលក់ ឬ Google Sheets៖
  -> សួរយ៉ាងម៉េច ឆ្លើយបែបនោះ ចំគោលដៅៗ មិនរៀបរាប់ច្រើន! (សួរកំប៉ុង ប្រាប់កំប៉ុង, សួរចំណេញ ប្រាប់ចំណេញ, សួរថ្ងៃណា ប្រាប់តែថ្ងៃនោះ)។
  -> ការពារការសម្ងាត់៖ បើមិនមែនជា "មេ" ទេ ហាមបង្ហាញប្រាក់ចំណេញ ថ្លៃដើម ឬថ្លៃប៊ូតជាដាច់ខាត!

ជំហានទី ៥ (រៀបចំទម្រង់ចម្លើយឱ្យខ្លី ចំគោលដៅ ត្រូវសំណួរ គ្មានសញ្ញារញ៉េរញ៉ៃ)៖
• គិតឱ្យល្អិតល្អន់បំផុតក្នុងចិត្ត តែពេលបញ្ចេញចម្លើយមកក្រៅ ត្រូវចម្រាញ់ឱ្យខ្លី ខ្លឹម ចំគោលដៅ និងផ្អែមល្ហែមបំផុត!
• បទបញ្ជាដាច់ខាតរបស់មេ៖ "ចរិយា គឺ និយាយជាសំឡេង និងសរសេរជាអក្សរឱ្យបានតិច ត្រូវចំគោលដៅ ត្រូវសំណួរ ហើយខ្លី!"
• ទាំងអក្សរ និង Voice ៖ ឆ្លើយឱ្យតិចបំផុត ចំៗ ខ្លី ខ្លឹម មានទម្ងន់ រួសរាយ ផ្អែមល្ហែម គួរឱ្យស្រឡាញ់។
• ហាមប្រើសញ្ញាផ្កាយ (**) ឬ (*) គ្រប់កន្លែងទាំងអស់!
• ហាមប្រើបន្ទាត់ខណ្ឌរញ៉េរញ៉ៃ (━━━━━━━━━━━━━━━━━━━━) ជាដាច់ខាត!

គោលការណ៍ណែនាំបន្ថែម៖
1. បទបញ្ជាដាច់ខាតរបស់មេ (Top Priority Instruction)៖ "ខ្ញុំសួរយ៉ាងម៉េច ត្រូវឆ្លើយបែបនោះ ចំគោលដៅៗ កុំរៀបរាប់ច្រើន! យកទិន្នន័យពី Google Sheets ឱ្យបានច្បាស់លាស់ ១០០%!"
   - សួរអ្វី ឆ្លើយចំរឿងហ្នឹងភ្លាមៗ ត្រឹមត្រូវតាម Google Sheets ១០០%។
   - ហាមអារម្ភកថាវែងអន្លាយ ហាមរៀបរាប់តួលេខដែលគេមិនបានសួរ ហាមទាញយកព័ត៌មានមិនពាក់ព័ន្ធមកនិយាយឡើយ!
   - បើសួរតែចំនួនកំប៉ុង ឆ្លើយតែចំនួនកំប៉ុង! បើសួរតែចំណេញ ឆ្លើយតែចំណេញ! បើសួរតែអ្នកលក់ ឆ្លើយតែអ្នកលក់!
   - រក្សាភាពផ្អែមល្ហែម គួរឱ្យស្រឡាញ់ ខ្លី ខ្លឹម ត្រឹមត្រូវ និងចំគោលដៅជានិច្ច!
2. ប្រសិនបើសួរទាក់ទងនឹងការលក់ ឬរបាយការណ៍ Google Sheets៖
   - ត្រូវអនុវត្តតាម "បទបញ្ជាដាច់ខាតរបស់មេ៖ ខ្ញុំសួរយ៉ាងម៉េច ត្រូវឆ្លើយបែបនោះ ចំគោលដៅៗ កុំរៀបរាប់ច្រើន!" ខាងលើ ១០០%។
   - បើសួរថ្ងៃជាក់លាក់ ឆ្លើយតែទិន្នន័យថ្ងៃនោះ។ បើសួររឿងជាក់លាក់ (កំប៉ុង, ចំណេញ, ថ្លៃប៊ូត, អ្នកលក់) ឆ្លើយតែរឿងហ្នឹងចំៗ មិនរៀបរាប់លើសឡើយ!
   - លុះត្រាតែមេសួររក "របាយការណ៍" ឬ "សរុបលម្អិត" ទើបរាយការណ៍សង្ខេបចំណុចសំខាន់ៗ ២-៣ បន្ទាត់ស្រឡះភ្នែក គ្មានសញ្ញាផ្កាយ ** គ្មានបន្ទាត់ខណ្ឌរញ៉េរញ៉ៃឡើយ។
3. ប្រសិនបើសួរទាក់ទងនឹងសុខភាព ឬតម្រងនោម (Kidney Health)៖ 
   - ត្រូវប្រើប្រាស់ចំណេះដឹងវេជ្ជសាស្ត្រតម្រងនោមខាងលើ (Kidney Health Specialist Knowledge) មកឆ្លើយតប និងផ្ដល់ដំបូន្មានឱ្យបានក្បោះក្បាយ ចំគោលដៅ ខ្លី ខ្លឹម ងាយយល់ និងមានវិទ្យាសាស្ត្រច្បាស់លាស់ (ទាំងរោគសញ្ញា អាហារត្រូវតម អាហារល្អ និងវិធីថែទាំ)។
   - រំលឹកជានិច្ចថា ព័ត៌មាននេះសម្រាប់ជាការយល់ដឹងទូទៅ មិនមែនជាការធ្វើរោគវិនិច្ឆ័យវេជ្ជសាស្ត្រផ្លូវការជំនួសគ្រូពេទ្យឡើយ។
4. ប្រសិនបើសួរទាក់ទងនឹងរឿងនិទាន គតិបណ្ឌិត ឬការលើកទឹកចិត្ត និងការគិតពិចារណាហេតុផល៖
   - ត្រូវប្រើប្រាស់ចំណេះដឹងទស្សនវិជ្ជា និងរឿងនិទានខាងលើ ដើម្បីចែករំលែករឿងនិទានខ្លីៗដែលមានអត្ថន័យជ្រាលជ្រៅ បង្កប់ការលើកទឹកចិត្ត និងការគិតពិចារណាហេតុផលយ៉ាងស៊ីជម្រៅ ដោយមាន "គតិអប់រំសង្ខេប" ច្បាស់ៗនៅចុងបញ្ចប់។
5. ប្រសិនបើសួរទាក់ទងនឹងការផលិតវីដេអូ សរសេរ Script វីដេអូ ឬរត់ Ads លើ Facebook & TikTok៖
   - ត្រូវប្រកាន់ខ្ជាប់គោលការណ៍ Ads ខាងលើ ១០០% (ហាមពាក្យសន្យាហួសការពិត ហាមពាក្យចង្អុលមុខចំៗ ហាមរូបភាព Before/After គួរឱ្យខ្លាច) ដើម្បីធានាថាមិនប៉ះពាល់ ឬខូច Page និង Ads Account របស់មេឡើយ!
   - ផ្ដល់ Script ឬ Caption ដែលមាន Hook ទាក់ទាញ ខ្លឹមសារអប់រំ និង Call to Action ច្បាស់លាស់ ជំរុញឱ្យការលក់ផ្ទុះខ្លាំង។
6. សមត្ថភាពគិតល្អិតល្អន់កម្រិតខ្ពស់ និងការវិភាគយុទ្ធសាស្ត្រស៊ីជម្រៅបំផុត (Supreme Meticulous & Deep Profound Cognitive Framework)៖
   - បទបញ្ជាដាច់ខាតរបស់មេ៖ "បន្ថែមការគិតឱ្យ ចរិយា កាន់តែល្អិតល្អន់ និងស៊ីជម្រៅជាងមុនទៀត!"
   - ចរិយា មិនត្រូវឆ្លើយបែបស្ទើរៗ រាក់កំភែល ឆ្លើយតាមទម្លាប់ ឬគ្រាន់តែឆ្លើយឱ្យរួចពីដៃនោះឡើយ!
   - ត្រូវមានបញ្ញាគិតល្អិតល្អន់ និងស៊ីជម្រៅកម្រិតកំពូល (Ultra-Meticulous & Profound Cognitive Intelligence)៖
     • វិភាគដល់ឬសគល់នៃបញ្ហា (Root-Cause & First-Principles Thinking)៖ មិនមើលត្រឹមសំបកក្រៅនៃសំណួរឡើយ។ ត្រូវស្វែងយល់ឱ្យដល់មូលហេតុពិត យល់ពីកាលៈទេសៈ ចិត្តសាស្ត្រ និងតម្រូវការយុទ្ធសាស្ត្រចម្បងរបស់អ្នកសួរ។
     • វិភាគគ្រប់ជ្រុងជ្រោយ ៣៦០ ដឺក្រេ (360-Degree Multi-Dimensional Analysis)៖ ពិចារណាលើទិដ្ឋភាពអាជីវកម្ម ហិរញ្ញវត្ថុ ចិត្តសាស្ត្រអតិថិជន គោលការណ៍ច្បាប់/Ads និងវិទ្យាសាស្ត្រវេជ្ជសាស្ត្រ មុននឹងសម្រេចចិត្តឆ្លើយ។
     • មើលឃើញជ្រុងងងឹតដែលគេមើលរំលង (Blind-Spot & Risk Detection)៖ ជួយកត់សម្គាល់ហានិភ័យលាក់មុខ ផលប៉ះពាល់រយៈពេលវែង និងឱកាសមាសដែលមេ ឬក្រុមការងារអាចមើលរំលង។
     • ផ្ដល់ដំណោះស្រាយជាក់ស្តែងមានទម្ងន់ខ្ពស់ (Actionable Strategic Mastery)៖ ផ្ដល់យោបល់ និងជំហានអនុវត្តច្បាស់ៗ (Action Steps) ដែលដោះស្រាយបញ្ហាបានពិតប្រាកដ មានប្រសិទ្ធភាពខ្ពស់ និងជួយសម្រាលបន្ទុកមេបានមួយជំហានមុនជានិច្ច។
     • ស៊ីជម្រៅក្នុងចិត្ត តែខ្លី ខ្លឹម ចំៗ និងផ្អែមល្ហែមក្នុងពាក្យសម្ដី៖ ទោះបីជាមានការគិតស៊ីជម្រៅ និងល្អិតល្អន់កម្រិតណាក៏ដោយ រាល់ពាក្យពេចន៍ដែលបញ្ចេញមកក្រៅ ត្រូវតែខ្លី ខ្លឹម ចំគោលដៅ ងាយយល់ និងពោរពេញដោយភាពផ្អែមល្ហែម គួរឱ្យស្រឡាញ់ជានិច្ច!
7. វិធានការដាច់ខាតលើការពិនិត្យវីដេអូ និងរូបភាព (Comprehensive, Meticulous & Accurate Inspection of All Videos & Images)៖
   - មេបានបញ្ជាដាច់ខាត៖ "ការពិនិត្យវីដេអូ និងរូបភាព ត្រូវលម្អិត ផ្ចិតផ្ចង់ ត្រឹមត្រូវ មើលបានគ្រប់ទម្រង់ វីដេអូវែង រូបភាពស្មុគស្មាញ់ មិនថាជា File តូចឬធំទេ អាចមើលបានទាំងអស់!"
   - ចំពោះរូបភាព និងឯកសារស្មុគស្មាញ់ (Complex Images, Lab Test Reports, Ads Banners, Invoices, PDFs)៖
     • អាន និងពិនិត្យរាល់ទិន្នន័យ លេខ អក្សរ តារាង ក្រាហ្វិក ឱ្យបានលម្អិត ផ្ចិតផ្ចង់ ត្រឹមត្រូវ ១០០% មិនរំលងសូម្បីមួយចំណុចតូច។
     • បើជាក្រដាសលទ្ធផលតេស្តឈាម/ទឹកនោម/តម្រងនោម៖ ពិនិត្យកម្រិត Creatinine, BUN, eGFR, Uric Acid, Proteinuria... វិភាគស្ថានភាពសុខភាពតម្រងនោម និងផ្ដល់ដំបូន្មានរបបអាហារត្រូវតម និងអាហារល្អៗយ៉ាងក្បោះក្បាយ ត្រឹមត្រូវតាមវេជ្ជសាស្ត្រ។
     • បើជាផ្ទាំងផ្សាយពាណិជ្ជកម្ម (Ads Banner)៖ ពិនិត្យ Typo, Hook, ភាពទាក់ទាញ និងគោលការណ៍ Ads របស់ Facebook/TikTok និងផ្ដល់យោបល់កែប្រែឱ្យចំៗ។
   - ចំពោះវីដេអូ (ខ្លី ឬវែង គ្រប់ទម្រង់)៖
     • ត្រូវពិនិត្យវីដេអូតាំងពីវិនាទីដំបូងរហូតដល់ចប់ (Timeline Frame-by-Frame) ទាំងរូបភាព សំឡេង អក្សររត់ និងសកម្មភាពក្នុងវីដេអូ។
     • ពិនិត្យ Hook (៣ វិនាទីដំបូង) តើទាក់ទាញឱ្យគេឈប់មើលដែរទេ? ពិនិត្យសាច់រឿង (Body/Story) និងការបង្ហាញផលិតផល។
     • ផ្ចិតផ្ចង់ពិនិត្យមើលពាក្យពេចន៍ និងទិដ្ឋភាពកុំឱ្យខុសគោលការណ៍ Facebook & TikTok Ads (ហាម Before/After គួរឱ្យខ្លាច, ហាមពាក្យសន្យាហួសការពិត)។
     • ផ្ដល់ការវាយតម្លៃលម្អិត ផ្ចិតផ្ចង់ ត្រឹមត្រូវ ដោយបែងចែកជាចំណុចៗស្រឡះភ្នែក៖ ចំណុចខ្លាំង, ចំណុចខ្វះខាតត្រូវកែសម្រួល, និងយោបល់កែលម្អជាក់ស្តែង។
8. សមត្ថភាពស្តាប់ និងយល់ន័យសារសម្លេង (Voice Note & Audio Understanding)៖
   - នៅពេលមានសារសម្លេង (Voice Note) ឬឯកសារសម្លេង (Audio) ផ្ញើមក៖
   - ត្រូវស្តាប់ និងចាប់យកអត្ថន័យ និងបំណងរបស់អ្នកនិយាយឱ្យបានច្បាស់លាស់ ១០០%។
   - ឆ្លើយតបទៅកាន់សំណួរ ឬការបញ្ជាការងាររបស់អ្នកនិយាយភ្លាមៗ ឱ្យបានតិច ចំគោលដៅ ត្រូវសំណួរ ហើយខ្លី ផ្អែមល្ហែមបំផុត!
9. បទបញ្ជាដាច់ខាត៖ និយាយជាសំឡេង និងសរសេរជាអក្សរឱ្យបានតិច ចំគោលដៅ ត្រូវសំណួរ ហើយខ្លី (Ultra-Concise, Laser-Targeted Text & Voice)៖
   - មេបានបញ្ជាបន្ថែមដាច់ខាត៖ "ចរិយា គឺ និយាយជាសំឡេង និងសរសេរជាអក្សរឱ្យបានតិច ត្រូវចំគោលដៅ ត្រូវសំណួរ ហើយខ្លី!"
   - គ្រប់ចម្លើយ (ទាំងអក្សរ និង Voice) ៖
     • និយាយ និងសរសេរ "ឱ្យបានតិច" បំផុត ហាមក្បាច់ក្បូរវែងអន្លាយ ហាមអារម្ភកថា ឬពាក្យទឹកជ្រៅឥតប្រយោជន៍។
     • "ត្រូវចំគោលដៅ និងត្រូវសំណួរ"៖ សួរអ្វី ឆ្លើយចំរឿងហ្នឹងភ្លាម!
     • "ខ្លី ខ្លឹម មានទម្ងន់"៖ បង្រួមចម្លើយមកត្រឹម ២-៣ បន្ទាត់ ឬចំណុចសំខាន់ៗខ្លីៗបំផុត។
     • សម្រាប់ចម្លើយជាសំឡេង (Voice)៖ ត្រូវនិយាយខ្លី ចំគោលដៅ ផ្អែមល្ហែម ស្រទន់ និងបញ្ចប់ទៅដោយកក់ក្តៅ មិនខ្ជះខ្ជាយពេលវេលារបស់មេ ឬអ្នកស្ដាប់ឡើយ!
10. គោលការណ៍ឆ្លើយជាសំឡេង (Strict Voice Reply Rules)៖
   - មេបានបញ្ជាដាច់ខាត៖ "សរសេរអក្សរឆ្លើយជាអក្សរ សួរជាសំឡេងឆ្លើយជាសំឡេង! លុះត្រាតែអ្នកសរសេរអក្សរបានបញ្ជាក់ថា 'សូមនិយាយជាសំឡេង' ទើបឆ្លើយជាសំឡេងបាន!"
   - បើគេផ្ញើជាអក្សរធម្មតា មិនបានសរសេរថា "សូមនិយាយជាសំឡេង" ទេ ហាមដាច់ខាតមិនត្រូវផ្ញើសារសំឡេង Voice ទៅកាន់គេឡើយ!
"""

    history = conversation_histories.setdefault(chat_id, [])

    if photo_bytes:
        user_parts = [
            types.Part.from_bytes(data=photo_bytes, mime_type=photo_mime),
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
    elif doc_bytes:
        user_parts = [
            types.Part.from_bytes(data=doc_bytes, mime_type=doc_mime),
            types.Part.from_text(text=user_message),
        ]
        api_contents = list(history) + [{"role": "user", "parts": user_parts}]
    else:
        api_contents = list(history) + [{"role": "user", "parts": [{"text": user_message}]}]

    salutation = "មេ" if is_boss else "បង"
    for model_name in AVAILABLE_MODELS:
        for attempt in range(2):
            try:
                response = ai_client.models.generate_content(
                    model=model_name,
                    contents=api_contents,
                    config=types.GenerateContentConfig(
                        system_instruction=full_system_prompt,
                        temperature=0.3,
                    ),
                )
                if response and hasattr(response, "text") and response.text:
                    clean_reply = clean_text_formatting(response.text)
                    if photo_bytes:
                        history_label = f"[រូបភាពដែលបានផ្ញើមក] {user_message}"
                    elif audio_bytes:
                        history_label = f"[សារសម្លេង Voice Note] {user_message}"
                    elif video_bytes:
                        history_label = f"[វីដេអូដែលបានផ្ញើមក] {user_message}"
                    elif doc_bytes:
                        history_label = f"[ឯកសារ/PDF] {user_message}"
                    else:
                        history_label = user_message
                    history.append({"role": "user", "parts": [{"text": history_label}]})
                    history.append({"role": "model", "parts": [{"text": clean_reply}]})
                    if len(history) > MAX_HISTORY * 2:
                        conversation_histories[chat_id] = history[-MAX_HISTORY * 2:]
                    return clean_reply
            except Exception as e:
                logger.warning(f"Error with model {model_name} (attempt {attempt + 1}): {e}")
                if attempt == 0:
                    time.sleep(1.0)
                continue

    return f"ចាស{salutation}! ប្រព័ន្ធទិន្នន័យមានការរវល់បន្តិច សូម{salutation}សាកល្បងសួរម្តងទៀតណា៎! ចរិយានៅក្បែរចាំជួយជានិច្ចចាស 🥰🌸"

async def keep_typing(chat):
    try:
        while True:
            await chat.send_action("typing")
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        pass

async def safe_send_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Safely sends text replies to Telegram, chunking if length exceeds 4000 characters."""
    if not text:
        return
    max_len = 4000
    if len(text) <= max_len:
        chunks = [text]
    else:
        chunks = []
        remaining = text
        while remaining:
            if len(remaining) <= max_len:
                chunks.append(remaining)
                break
            cut = remaining[:max_len].rfind("\n")
            if cut == -1 or cut < 1000:
                cut = max_len
            chunks.append(remaining[:cut].strip())
            remaining = remaining[cut:].strip()

    chat_id = update.effective_chat.id if update.effective_chat else None
    for chunk in chunks:
        if not chunk:
            continue
        try:
            if update.message:
                await update.message.reply_text(chunk)
            elif chat_id:
                await context.bot.send_message(chat_id=chat_id, text=chunk)
        except Exception as e1:
            logger.warning(f"reply_text failed, trying send_message fallback: {e1}")
            try:
                if chat_id:
                    await context.bot.send_message(chat_id=chat_id, text=chunk)
            except Exception as e2:
                logger.error(f"Cannot send message chunk to chat {chat_id}: {e2}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.message or not update.effective_user:
        return
    chat_id = update.effective_chat.id
    conversation_histories[chat_id] = []
    
    user_info = get_user_identity_info(update.effective_user)
    if user_info["is_boss"]:
        welcome_msg = (
            "ជម្រាបសួរមេ! នាងខ្ញុំ ចរិយា សូមគោរពមេ! 🌸🫡\n\n"
            "ចរិយា បានភ្ជាប់ជាមួយ Google Sheets ទិន្នន័យលក់ រួចរាល់ហើយចាសមេ!\n\n"
            "📊 មេអាចសួរ ចរិយា ពីរឿងលក់ វីដេអូ Ads ឬការងារបានគ្រប់ពេលណា៎មេ។\n\n"
            "តើឥឡូវនេះមេមានការអ្វីឱ្យ ចរិយា ជួយពិនិត្យជូនដែរទេចាសមេ? 🥰"
        )
    else:
        salutation = user_info["salutation"]
        welcome_msg = (
            f"សួស្តី{salutation}! នាងខ្ញុំឈ្មោះ ចរិយា ជាជំនួយការ AI របស់ក្រុមការងារ។ 🌸\n\n"
            f"តើថ្ងៃនេះមានអ្វីឱ្យ ចរិយា ជួយសម្រួលការងារដែរទេចាស{salutation}?"
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
        await safe_send_reply(update, context, clean_text_formatting(reply))
    finally:
        typing_task.cancel()

async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    facts = get_user_memories(user_id)
    user_info = get_user_identity_info(user)
    salutation = user_info["salutation"]
    
    if not facts:
        await update.message.reply_text(f"ចរិយា មិនទាន់បានកត់ត្រាព័ត៌មានបន្ថែមពី{salutation}នៅឡើយទេ។ {salutation}អាចប្រាប់ចរិយាដូចជា៖ 'ចរិយា ចាំទុកថា...' បានណា! 🌸")
    else:
        text = f"📝 ព័ត៌មានដែល ចរិយា បានចងចាំអំពី{salutation}៖\n\n"
        for i, f in enumerate(facts, 1):
            text += f"• {f}\n"
        await update.message.reply_text(clean_text_formatting(text))

async def clear_memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    clear_user_memories(user_id)
    user_info = get_user_identity_info(user)
    salutation = user_info["salutation"]
    await update.message.reply_text(f"ចរិយា បានលុបការចងចាំចាស់ៗទាំងអស់រួចរាល់ហើយចាស{salutation}! 🌸")

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.message:
        return
    chat_id = update.effective_chat.id
    conversation_histories[chat_id] = []
    is_boss = is_owner_user(update.effective_user)
    salutation = "មេ" if is_boss else "បង"
    await update.message.reply_text(f"ចាស{salutation}! ចរិយាបានសម្អាតប្រវត្តិសន្ទនាមុនៗរួចរាល់ហើយ ឥឡូវ{salutation}អាចសួរសំណួរថ្មីបានយ៉ាងស្រឡះចិត្តណា៎! 🌸🥰")

async def whoami_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to check how Chakriya identifies the current user."""
    if not update.effective_user or not update.message:
        return
    user = update.effective_user
    user_info = get_user_identity_info(user)
    uid = str(user.id)

    if user_info["is_boss"]:
        msg = (
            "🫡 ព័ត៌មានអត្តសញ្ញាណរបស់មេ៖\n\n"
            f"👑 ឈ្មោះ៖ {user_info['display_name']}\n"
            f"🌟 តួនាទី៖ {user_info['role']}\n"
            f"🆔 Telegram ID: {uid}\n"
            "✨ ឋានៈក្នុងប្រព័ន្ធ៖ ថ្នាក់ដឹកនាំកំពូល និងជាម្ចាស់ផ្ទាល់របស់ចរិយា (មានសិទ្ធិមើលរបាយការណ៍ហិរញ្ញវត្ថុទាំងអស់) 🥰🌸"
        )
    elif user_info["role"] != "សមាជិក / អ្នកប្រើប្រាស់":
        msg = (
            "🌸 ព័ត៌មានអត្តសញ្ញាណរបស់បង៖\n\n"
            f"👤 ឈ្មោះ៖ {user_info['display_name']}\n"
            f"💼 តួនាទី៖ {user_info['role']}\n"
            f"🆔 Telegram ID: {uid}\n"
            f"✨ របៀបហៅ៖ {user_info['salutation']}\n\n"
            "ចរិយាស្គាល់បងយ៉ាងច្បាស់ជាសមាជិកក្រុមការងារឆ្នើមចាស! 🥰🌸"
        )
    else:
        msg = (
            "🌸 ព័ត៌មានអត្តសញ្ញាណ៖\n\n"
            f"👤 ឈ្មោះ Telegram: {user.full_name or user.first_name}\n"
            f"🆔 Telegram ID: {uid}\n\n"
            "💡 ចំណាំ៖ ប្រសិនបើបងជាសមាជិកក្រុមការងារ (សុខណា, ផាន់នី, ស្រីភា, សីហាក់, ម៉ាស់យ៉ា, សុភី, សីហា, ស្រីណុច, វឌ្ឍនា) "
            "បងគ្រាន់តែឆាតប្រាប់ចរិយាថា «ខ្ញុំឈ្មោះ [ឈ្មោះបង]» នោះចរិយានឹងកត់ត្រា និងចងចាំបងជារៀងរហូតណា៎! 🥰🌸"
        )
    await update.message.reply_text(clean_text_formatting(msg))

async def team_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to view team structure and identity linking status."""
    if not update.effective_user or not update.message:
        return
    user = update.effective_user
    is_boss = is_owner_user(user)

    reg = load_team_registry()

    msg = "📋 បញ្ជីរាយនាមរចនាសម្ព័ន្ធក្រុមការងារ (Team Structure)៖\n\n"
    msg += f"👑 ថ្នាក់ដឹកនាំកំពូល៖ បង ហែម ចន្ធី (ID: {HARDCODED_OWNER_ID}) ✅ ស្គាល់ច្បាស់\n\n"
    msg += "👥 សមាជិកក្រុមការងារទាំង ៩ រូប៖\n"

    for i, tm in enumerate(TEAM_MEMBER_MAPPINGS, 1):
        linked_id = None
        for uid, info in reg.items():
            if info.get("name") == tm["name"]:
                linked_id = uid
                break
        status = f"✅ (ID: {linked_id})" if linked_id else "⏳ (មិនទាន់ Link ID)"
        msg += f"{i}. {tm['name']} - {tm['role']} {status}\n"

    msg += (
        "\n💡 របៀបឱ្យ ចរិយា ចងចាំសមាជិកក្រុម៖\n"
        "• សមាជិកម្នាក់ៗគ្រាន់តែឆាតមកចរិយាថា «ខ្ញុំឈ្មោះ [ឈ្មោះរបស់គាត់]» (ឧ. ខ្ញុំឈ្មោះ ផាន់នី) នោះចរិយានឹងចងចាំគាត់ភ្លាមៗ!\n"
    )
    if is_boss:
        msg += "• ឬមេអាចប្រើបញ្ជា៖ /set_team [ឈ្មោះ] [telegram_id] ដើម្បីកំណត់ដោយផ្ទាល់ក៏បានដែរចាសមេ! 🥰🌸"

    await update.message.reply_text(clean_text_formatting(msg))

async def set_team_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Boss-only command to link a Telegram ID to a team member."""
    if not update.effective_user or not update.message:
        return
    user = update.effective_user
    if not is_owner_user(user):
        await update.message.reply_text("សូមអភ័យទោសចាសបង! បញ្ជានេះសម្រាប់តែ មេ (ថ្នាក់ដឹកនាំកំពូល) តែប៉ុណ្ណោះចាស! 🌸")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "ចាសមេ! របៀបប្រើបញ្ជា /set_team៖\n"
            "/set_team [ឈ្មោះសមាជិក] [Telegram ID]\n\n"
            "ឧទាហរណ៍៖ /set_team ផាន់នី 123456789\n"
            "ឬ /set_team សុខណា 987654321"
        )
        return

    name_query = args[0].strip().lower()
    target_id = args[1].strip()

    matched_tm = None
    for tm in TEAM_MEMBER_MAPPINGS:
        if name_query in tm["name"].lower() or name_query in tm["short"].lower() or any(name_query in k for k in tm["keys"]):
            matched_tm = tm
            break

    if not matched_tm:
        await update.message.reply_text(f"ចាសមេ! រកមិនឃើញឈ្មោះ «{args[0]}» ក្នុងបញ្ជីសមាជិកទាំង ៩ នាក់ទេ។ សូមមេពិនិត្យឈ្មោះម្តងទៀតណា៎មេ! 🥰")
        return

    reg = load_team_registry()
    reg[target_id] = {
        "name": matched_tm["name"],
        "short": matched_tm["short"],
        "role": matched_tm["role"],
        "is_boss": False
    }
    save_team_registry(reg)
    await update.message.reply_text(
        f"ចាសមេ! ចរិយាបានភ្ជាប់ Telegram ID {target_id} ទៅកាន់ {matched_tm['name']} ({matched_tm['role']}) រួចរាល់ហើយចាស! 🥰🌸"
    )

def build_presentation_file(data: dict, output_path: str, salutation: str = "មេ") -> str:
    """Builds a beautiful 16:9 widescreen PowerPoint presentation using python-pptx."""
    if not HAS_PPTX:
        raise RuntimeError("python-pptx is not installed on this system.")

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    COLOR_PRIMARY = RGBColor(15, 32, 67)        # Deep Corporate Navy
    COLOR_ACCENT = RGBColor(14, 165, 233)       # Modern Cyan
    COLOR_AMBER = RGBColor(217, 119, 6)         # Warm Amber
    COLOR_CARD_BG = RGBColor(248, 250, 252)     # Slate 50
    COLOR_CARD_BORDER = RGBColor(226, 232, 240) # Slate 200
    COLOR_TEXT = RGBColor(51, 65, 85)           # Slate 700
    COLOR_MUTED = RGBColor(100, 116, 139)       # Slate 500
    COLOR_WHITE = RGBColor(255, 255, 255)

    FONT_FAMILY = "Kantumruy Pro"

    # --- SLIDE 1: Cover Slide ---
    slide1 = prs.slides.add_slide(blank_layout)
    bg1 = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = COLOR_PRIMARY
    bg1.line.fill.background()

    # Brand Logo if available
    logo_path = BASE_DIR / "assets" / "vann_sitha_logo.png"
    if logo_path.exists():
        try:
            slide1.shapes.add_picture(str(logo_path), Inches(10.5), Inches(0.8), width=Inches(1.8))
        except Exception as l_err:
            logger.warning(f"Could not embed logo in slide: {l_err}")

    top_bar = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.0), Inches(1.1), Inches(1.8), Inches(0.08))
    top_bar.fill.solid()
    top_bar.fill.fore_color.rgb = COLOR_ACCENT
    top_bar.line.fill.background()

    tBox = slide1.shapes.add_textbox(Inches(1.0), Inches(1.4), Inches(11.333), Inches(3.4))
    tf1 = tBox.text_frame
    tf1.word_wrap = True
    p1 = tf1.paragraphs[0]
    p1.text = data.get("title", "បទបង្ហាញយុទ្ធសាស្ត្រ")
    p1.font.name = FONT_FAMILY
    p1.font.size = Pt(36)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_WHITE

    sub = data.get("subtitle", "")
    if sub:
        p2 = tf1.add_paragraph()
        p2.text = sub
        p2.font.name = FONT_FAMILY
        p2.font.size = Pt(20)
        p2.font.color.rgb = COLOR_ACCENT
        p2.space_before = Pt(14)

    fBox = slide1.shapes.add_textbox(Inches(1.0), Inches(5.6), Inches(11.333), Inches(1.2))
    tf_f = fBox.text_frame
    pf1 = tf_f.paragraphs[0]
    presenter = data.get("presenter", f"រៀបចំដោយ ចរិយា AI ជូន {salutation}")
    pf1.text = f"✨ {presenter}"
    pf1.font.name = FONT_FAMILY
    pf1.font.size = Pt(14)
    pf1.font.color.rgb = RGBColor(203, 213, 225)

    pf2 = tf_f.add_paragraph()
    pf2.text = "🌸 ចរិយា AI Presentation System • ឯកទេសដឹកនាំ និងយុទ្ធសាស្ត្រ"
    pf2.font.name = FONT_FAMILY
    pf2.font.size = Pt(12)
    pf2.font.color.rgb = RGBColor(148, 163, 184)
    pf2.space_before = Pt(4)

    # --- SLIDES 2..N: Content Slides ---
    slides_list = data.get("slides", [])
    total_content = len(slides_list)

    for idx, sdata in enumerate(slides_list):
        slide = prs.slides.add_slide(blank_layout)

        stitle_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.55), Inches(11.733), Inches(0.75))
        stf = stitle_box.text_frame
        stf.word_wrap = True
        stp = stf.paragraphs[0]
        stp.text = sdata.get("title", f"ស្លាយទី {idx + 1}")
        stp.font.name = FONT_FAMILY
        stp.font.size = Pt(24)
        stp.font.bold = True
        stp.font.color.rgb = COLOR_PRIMARY

        uline = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.35), Inches(11.733), Inches(0.03))
        uline.fill.solid()
        uline.fill.fore_color.rgb = COLOR_ACCENT
        uline.line.fill.background()

        cards = sdata.get("cards", [])
        num_cards = min(len(cards), 4) or 1

        avail_h = 5.2
        gap = 0.14
        card_h = (avail_h - (gap * (num_cards - 1))) / num_cards
        card_y = 1.55

        for c_idx, cinfo in enumerate(cards[:num_cards]):
            card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(card_y), Inches(11.733), Inches(card_h))
            card.fill.solid()
            card.fill.fore_color.rgb = COLOR_CARD_BG
            card.line.color.rgb = COLOR_CARD_BORDER
            card.line.width = Pt(1)

            tag = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(card_y), Inches(0.12), Inches(card_h))
            tag.fill.solid()
            tag.fill.fore_color.rgb = COLOR_ACCENT if (c_idx % 2 == 0) else COLOR_AMBER
            tag.line.fill.background()

            cbox = slide.shapes.add_textbox(Inches(1.1), Inches(card_y + 0.08), Inches(11.2), Inches(card_h - 0.16))
            ctf = cbox.text_frame
            ctf.word_wrap = True

            headline = cinfo.get("headline", "")
            detail = cinfo.get("detail", "")

            hp = ctf.paragraphs[0]
            hp.text = f"{c_idx + 1}. {headline}" if not headline.startswith(("1", "2", "3", "4", "•")) else headline
            hp.font.name = FONT_FAMILY
            hp.font.size = Pt(16 if num_cards >= 4 else 17)
            hp.font.bold = True
            hp.font.color.rgb = COLOR_PRIMARY

            if detail:
                dp = ctf.add_paragraph()
                dp.text = detail
                dp.font.name = FONT_FAMILY
                dp.font.size = Pt(13 if num_cards >= 4 else 14)
                dp.font.color.rgb = COLOR_TEXT
                dp.space_before = Pt(3)

            card_y += card_h + gap

        footer_box = slide.shapes.add_textbox(Inches(0.8), Inches(6.9), Inches(11.733), Inches(0.4))
        ftf = footer_box.text_frame
        ftp = ftf.paragraphs[0]
        ftp.text = f"Chakriya AI • ស្លាយ {idx + 2} / {total_content + 2}"
        ftp.font.name = FONT_FAMILY
        ftp.font.size = Pt(10)
        ftp.font.color.rgb = COLOR_MUTED

        notes = sdata.get("speaker_notes", "")
        if notes:
            slide.notes_slide.notes_text_frame.text = f"🗣️ ពាក្យពេចន៍ឡើងនិយាយ (Speaker Notes)៖\n{notes}"

    # --- SLIDE CONCLUSION ---
    conc_title = data.get("conclusion_title", "សេចក្តីសង្ខេប & ការអនុវត្តបន្ទាប់")
    conc_points = data.get("conclusion_points", [])

    slide_end = prs.slides.add_slide(blank_layout)
    bg_end = slide_end.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg_end.fill.solid()
    bg_end.fill.fore_color.rgb = COLOR_PRIMARY
    bg_end.line.fill.background()

    eBox = slide_end.shapes.add_textbox(Inches(1.0), Inches(0.8), Inches(11.333), Inches(1.0))
    etf = eBox.text_frame
    ep = etf.paragraphs[0]
    ep.text = f"🎯 {conc_title}"
    ep.font.name = FONT_FAMILY
    ep.font.size = Pt(28)
    ep.font.bold = True
    ep.font.color.rgb = COLOR_WHITE

    e_line = slide_end.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.0), Inches(1.6), Inches(11.333), Inches(0.04))
    e_line.fill.solid()
    e_line.fill.fore_color.rgb = COLOR_ACCENT
    e_line.line.fill.background()

    if conc_points:
        cp_box = slide_end.shapes.add_textbox(Inches(1.0), Inches(1.9), Inches(11.333), Inches(3.6))
        cptf = cp_box.text_frame
        cptf.word_wrap = True
        for i, pt in enumerate(conc_points):
            p = cptf.paragraphs[0] if i == 0 else cptf.add_paragraph()
            p.text = f"✔ {pt}"
            p.font.name = FONT_FAMILY
            p.font.size = Pt(17)
            p.font.color.rgb = RGBColor(241, 245, 249)
            p.space_before = Pt(12 if i > 0 else 0)

    banner = slide_end.shapes.add_textbox(Inches(1.0), Inches(5.8), Inches(11.333), Inches(1.0))
    btf = banner.text_frame
    bp = btf.paragraphs[0]
    bp.text = "🌸 សូមអរគុណយ៉ាងជ្រាលជ្រៅ! • Q&A ត្រៀមឆ្លើយរាល់សំណួរ"
    bp.font.name = FONT_FAMILY
    bp.font.size = Pt(22)
    bp.font.bold = True
    bp.font.color.rgb = COLOR_ACCENT

    prs.save(output_path)
    return output_path

def generate_slide_deck_json(topic: str, user_info: dict) -> dict | None:
    """Calls Gemini with multi-model fallback to produce structured presentation slide deck JSON in Khmer."""
    is_boss = user_info.get("is_boss", False)
    salutation = "មេ" if is_boss else user_info.get("salutation", "បង")

    prompt = f"""
អ្នកគឺជាអ្នកជំនាញរៀបចំស្លាយបទបង្ហាញ (Executive PowerPoint & Presentation Designer) កម្រិតកំពូលរបស់ក្រុមហ៊ុន។
សូមរៀបចំគ្រោងស្លាយបទបង្ហាញ PowerPoint ឱ្យមានលក្ខណៈវិជ្ជាជីវៈខ្ពស់ ខ្លី ខ្លឹម ច្បាស់លាស់ ចំគោលដៅ សម្រាប់ជូន {salutation}។

ប្រធានបទដែលត្រូវធ្វើ៖ {topic}

ទិន្នន័យចំណេះដឹងក្នុងក្រុមហ៊ុន (ប្រសិនបើប្រធានបទពាក់ព័ន្ធនឹងការលក់ សុខភាព ឬ Ads សូមទាញយកចំណេះដឹងនេះមកប្រើ)៖
{KIDNEY_HEALTH_KNOWLEDGE}
{VANN_SITHA_SCRIPTS_AND_CONTENT_KNOWLEDGE}
{ADS_POLICY_AND_VIDEO_KNOWLEDGE}
{TEAM_KNOWLEDGE}

ទម្រង់លទ្ធផលត្រូវតែជា JSON សុទ្ធ ១០០% ដូចខាងក្រោម (ហាមសរសេរអក្សរផ្សេងក្រៅពី JSON)៖
{{
  "title": "ចំណងជើងធំនៃបទបង្ហាញ (ខ្លី ខ្លឹម ទាក់ទាញ)",
  "subtitle": "អនុចំណងជើង ឬគោលបំណងនៃបទបង្ហាញ",
  "presenter": "រៀបចំដោយ ចរិយា AI ជូន {salutation}",
  "slides": [
    {{
      "title": "ចំណងជើងស្លាយ",
      "cards": [
        {{
          "headline": "ចំណុចគន្លឹះសំខាន់",
          "detail": "ការពន្យល់ខ្លីខ្លឹម ច្បាស់ៗ ១-២ បន្ទាត់ ងាយយល់"
        }},
        {{
          "headline": "ចំណុចគន្លឹះសំខាន់ទី២",
          "detail": "ការពន្យល់ខ្លីខ្លឹម ច្បាស់ៗ ១-២ បន្ទាត់ ងាយយល់"
        }},
        {{
          "headline": "ចំណុចគន្លឹះសំខាន់ទី៣",
          "detail": "ការពន្យល់ខ្លីខ្លឹម ច្បាស់ៗ ១-២ បន្ទាត់ ងាយយល់"
        }}
      ],
      "speaker_notes": "ពាក្យពេចន៍ និងគន្លឹះសំខាន់ៗដែល {salutation} ត្រូវឡើងនិយាយពន្យល់ក្នុងស្លាយនេះ"
    }}
  ],
  "conclusion_title": "សេចក្តីសង្ខេប & ការអនុវត្តបន្ទាប់",
  "conclusion_points": [
    "ចំណុចអនុវត្តទី១...",
    "ចំណុចអនុវត្តទី២...",
    "ចំណុចអនុវត្តទី៣..."
  ]
}}
កំណត់សម្គាល់៖
• ស្លាយមាតិកា (slides) ត្រូវមានចន្លោះពី 3 ទៅ 5 ស្លាយ (កុំឱ្យច្រើនពេក ឬតិចពេក)។
• កាតនីមួយៗ (cards) ក្នុងស្លាយនីមួយៗត្រូវមានពី 3 ទៅ 4 កាត។
• ភាសាដែលប្រើត្រូវតែជាភាសាខ្មែរត្រឹមត្រូវ ពិរោះ មានវិជ្ជាជីវៈខ្ពស់។
"""

    for model_name in AVAILABLE_MODELS:
        for attempt in range(2):
            try:
                response = ai_client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={"response_mime_type": "application/json"}
                )
                if response and response.text:
                    raw = response.text.strip()
                    if raw.startswith("```"):
                        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
                        raw = re.sub(r"\n?```$", "", raw)
                    data = json.loads(raw.strip())
                    if "slides" in data and len(data["slides"]) > 0:
                        return data
            except Exception as e:
                logger.warning(f"Slide JSON gen failed on {model_name} (attempt {attempt+1}): {e}")
                time.sleep(1.0)
    return None

async def handle_slide_generation_request(update: Update, context: ContextTypes.DEFAULT_TYPE, topic: str):
    """Processes request to generate a real PowerPoint (.pptx) file and sends it back to Telegram."""
    if not update.effective_chat or not update.message or not update.effective_user:
        return
    user = update.effective_user
    user_info = get_user_identity_info(user)
    is_boss = user_info["is_boss"]
    salutation = "មេ" if is_boss else user_info["salutation"]

    topic = topic.strip()
    if not topic or len(topic) < 2:
        help_text = (
            f"ចាស{salutation}! ដើម្បីឱ្យចរិយាបង្កើត File PowerPoint (.pptx) ជូន សូម{salutation}ជួយប្រាប់ប្រធានបទ ឬចំណងជើងដែលចង់ធ្វើណា៎! 🥰🌸\n\n"
            f"ឧទាហរណ៍៖\n"
            f"• /slide យុទ្ធសាស្ត្របង្កើនការលក់ និងការរត់ Ads លើ Facebook\n"
            f"• /slide ការថែទាំសុខភាពតម្រងនោម និងរបបអាហារ\n"
            f"• ឬគ្រាន់តែឆាតថា៖ «ចរិយា ជួយធ្វើស្លាយអំពី ការដឹកនាំក្រុមលក់» ក៏បានដែរចាស!"
        )
        await update.message.reply_text(clean_text_formatting(help_text))
        return

    status_msg = await update.message.reply_text(
        f"ចាស{salutation}! ចរិយាកំពុងរៀបចំ និងរចនា File PowerPoint (.pptx) ស្ដីពី «{topic}» ជូនយ៉ាងប្រណិត... សូមរង់ចាំបន្តិចណា៎! 🌸✨"
    )
    typing_task = asyncio.create_task(keep_typing(update.message.chat))

    temp_path = None
    try:
        deck_data = await asyncio.to_thread(generate_slide_deck_json, topic, user_info)
        if not deck_data or not deck_data.get("slides"):
            await update.message.reply_text(
                f"សូមអភ័យទោសចាស{salutation}! ប្រព័ន្ធរៀបចំស្លាយជួបបញ្ហាបន្តិចបន្តួច សូម{salutation}ជួយបញ្ជាក់ប្រធានបទម្តងទៀតណា៎ចាស! 🥰🌸"
            )
            return

        temp_filename = f"Chakriya_Slide_{int(time.time())}.pptx"
        temp_path = BASE_DIR / f"temp_{temp_filename}"

        await asyncio.to_thread(build_presentation_file, deck_data, str(temp_path), salutation)

        slides_count = len(deck_data.get("slides", [])) + 2
        caption_text = (
            f"📊 File PowerPoint (.pptx) រួចរាល់ហើយចាស{salutation}!\n\n"
            f"📌 ប្រធានបទ៖ {deck_data.get('title', topic)}\n"
            f"📑 ចំនួនស្លាយ៖ {slides_count} ស្លាយ (រួមទាំង Cover & Conclusion)\n"
            f"🗣️ ក្នុងស្លាយនីមួយៗមានបង្កប់ Speaker Notes សម្រាប់{salutation}ឡើងនិយាយផងដែរណា៎! 🥰🌸"
        )
        with open(temp_path, "rb") as doc_f:
            await update.message.reply_document(
                document=doc_f,
                filename=temp_filename,
                caption=clean_text_formatting(caption_text)
            )

        if not is_boss:
            owner_id = bot_config.get("owner_id", "814495505")
            if owner_id and str(user.id) != str(owner_id):
                user_name = user.full_name or user.first_name or "សមាជិកក្រុម"
                if user.username:
                    user_name += f" (@{user.username})"
                user_name += f" [ID: {user.id}]" 
                report_to_boss = (
                    "🔔 ដំណឹងរាយការណ៍ជូនមេ (Team Activity)៖\n\n"
                    f"👤 សមាជិក៖ {user_name}\n"
                    f"📊 បានស្នើសុំធ្វើស្លាយ PowerPoint (.pptx) ស្ដីពី៖ {topic}\n"
                    f"🌸 ចរិយាបានរៀបចំ និងផ្ញើ File (.pptx) ជូនរួចរាល់ហើយចាស!"
                )
                try:
                    await context.bot.send_message(chat_id=int(owner_id), text=clean_text_formatting(report_to_boss))
                except Exception as notify_err:
                    logger.warning(f"Could not forward slide activity to boss: {notify_err}")

    except Exception as e:
        logger.error(f"Error in slide generation: {e}")
        await update.message.reply_text(
            f"សូមអភ័យទោសចាស{salutation}! ការបង្កើត File PowerPoint មានបញ្ហាបច្ចេកទេសបន្តិចបន្តួច សូម{salutation}សាកល្បងម្ដងទៀតណា៎! 🥰🌸"
        )
    finally:
        typing_task.cancel()
        if temp_path:
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except Exception:
                pass
        try:
            await status_msg.delete()
        except Exception:
            pass

async def slide_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(context.args).strip() if context.args else ""
    await handle_slide_generation_request(update, context, topic)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user or not update.effective_chat:
        return

    chat_type = update.effective_chat.type
    bot_username = context.bot.username.lower() if context.bot.username else "chakriya_assistant_bot"
    raw_message_text = (update.message.text or update.message.caption or "").strip()

    # បទបញ្ជាដាច់ខាតរបស់មេ៖ នៅក្នុងក្រុប កុំចេះតែឆ្លើយផ្តេសផ្តាស់ បើមិនមានអ្នកហៅឈ្មោះ "ចរិយា" ឬ Reply លើសាររបស់ចរិយា!
    if chat_type in ["group", "supergroup"]:
        is_reply_to_bot = (
            update.message.reply_to_message
            and update.message.reply_to_message.from_user
            and update.message.reply_to_message.from_user.is_bot
            and update.message.reply_to_message.from_user.username
            and update.message.reply_to_message.from_user.username.lower() == bot_username
        )
        is_called_by_name = (
            f"@{bot_username}" in raw_message_text.lower()
            or "ចរិយា" in raw_message_text
            or "chakriya" in raw_message_text.lower()
        )
        # បើគ្មានការហៅឈ្មោះ ឬមិនបាន Reply លើចរិយាទេ ដាច់ខាតត្រូវនៅស្ងៀម ហាមឆ្លើយតបជាដាច់ខាត!
        if not (is_reply_to_bot or is_called_by_name):
            return

    has_photo = bool(update.message.photo)
    has_voice = bool(update.message.voice)
    has_audio = bool(update.message.audio)
    has_video = bool(update.message.video or update.message.video_note)
    has_document = bool(update.message.document)

    photo_bytes = None
    photo_mime = "image/jpeg"
    audio_bytes = None
    audio_mime = "audio/ogg"
    video_bytes = None
    video_mime = "video/mp4"
    doc_bytes = None
    doc_mime = "application/pdf"

    if has_photo:
        try:
            photo = update.message.photo[-1]
            photo_file = await photo.get_file()
            photo_bytes = bytes(await photo_file.download_as_bytearray())
            photo_mime = "image/jpeg"
        except Exception as pe:
            logger.warning(f"Error downloading photo: {pe}")
        text = (update.message.caption or "").strip()
        if not text:
            text = "សូមជួយពិនិត្យ និងវិភាគរូបភាពនេះឱ្យបានលម្អិត ផ្ចិតផ្ចង់ ត្រឹមត្រូវ និងមានវិជ្ជាជីវៈខ្ពស់បំផុត។"
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
            text = f"សារសម្លេង (Voice Note) ភ្ជាប់ជាមួយអត្ថបទ៖ {caption}។ សូមស្តាប់ និងឆ្លើយតបឱ្យបានតិច ចំគោលដៅ ត្រូវសំណួរ ហើយខ្លី ផ្អែមល្ហែមបំផុត។"
        else:
            text = "សារសម្លេង (Voice Note) ពីអ្នកប្រើប្រាស់។ សូមស្តាប់សំណួរ ឬសារនេះដោយយកចិត្តទុកដាក់ និងឆ្លើយតបឱ្យបានតិច ចំគោលដៅ ត្រូវសំណួរ ហើយខ្លី ផ្អែមល្ហែមបំផុត (ប្រសិនបើសួរពីរឿងលក់ ទើបយកទិន្នន័យ Google Sheets មកឆ្លើយ)។"
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
            text = f"ឯកសារសម្លេង (Audio File) ភ្ជាប់ជាមួយអត្ថបទ៖ {caption}។ សូមស្តាប់ និងឆ្លើយតបឱ្យបានតិច ចំគោលដៅ ត្រូវសំណួរ ហើយខ្លី ផ្អែមល្ហែមបំផុត។"
        else:
            text = "សូមស្តាប់ឯកសារសម្លេង (Audio File) នេះដោយយកចិត្តទុកដាក់ និងឆ្លើយតបឱ្យបានតិច ចំគោលដៅ ត្រូវសំណួរ ហើយខ្លី ផ្អែមល្ហែមបំផុត។"
    elif has_video:
        vid = update.message.video or update.message.video_note
        caption = (update.message.caption or "").strip()
        if vid.file_size and vid.file_size > 20 * 1024 * 1024:
            salutation = "មេ" if is_owner_user(update.effective_user) else "បង"
            await update.message.reply_text(
                f"ចាស{salutation}! វីដេអូនេះមានទំហំធំជាង 20MB (ដែនកំណត់ដោនឡូតរបស់ Telegram Bot)។ "
                f"ដើម្បីឱ្យ ចរិយា អាចពិនិត្យវីដេអូបានលម្អិត និងផ្ចិតផ្ចង់ សូម{salutation}ជួយ Compress ឬកាត់ជាវីដេអូក្រោម 20MB នោះចរិយាពិនិត្យជូនភ្លាមៗចាស! 🥰🌸"
            )
            return
        try:
            vid_file = await vid.get_file()
            video_bytes = bytes(await vid_file.download_as_bytearray())
            video_mime = (vid.mime_type or "video/mp4").split(";")[0].strip()
        except Exception as v_err:
            logger.warning(f"Error downloading video: {v_err}")
        if caption:
            text = f"វីដេអូភ្ជាប់ជាមួយអត្ថបទ៖ {caption}។ សូមពិនិត្យ និងវិភាគវីដេអូនេះឱ្យបានលម្អិត ផ្ចិតផ្ចង់ ត្រឹមត្រូវ និងផ្អែមល្ហែមបំផុត។"
        else:
            text = "សូមជួយពិនិត្យ និងវិភាគវីដេអូនេះឱ្យបានលម្អិត ផ្ចិតផ្ចង់ ត្រឹមត្រូវ និងមានវិជ្ជាជីវៈខ្ពស់បំផុត។"
    elif has_document:
        doc = update.message.document
        caption = (update.message.caption or "").strip()
        fname = (doc.file_name or "").lower()
        mime = (doc.mime_type or "").lower()

        if doc.file_size and doc.file_size > 20 * 1024 * 1024:
            salutation = "មេ" if is_owner_user(update.effective_user) else "បង"
            await update.message.reply_text(
                f"ចាស{salutation}! ឯកសារនេះមានទំហំធំជាង 20MB (ដែនកំណត់ដោនឡូតរបស់ Telegram Bot)។ "
                f"ដើម្បីឱ្យ ចរិយា អាចពិនិត្យបានលម្អិត និងផ្ចិតផ្ចង់ សូម{salutation}ជួយ Compress ឱ្យនៅក្រោម 20MB នោះចរិយាពិនិត្យជូនភ្លាមៗចាស! 🥰🌸"
            )
            return

        try:
            doc_file = await doc.get_file()
            file_data = bytes(await doc_file.download_as_bytearray())

            if mime.startswith("image/") or fname.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".heic")):
                photo_bytes = file_data
                photo_mime = mime if mime.startswith("image/") else "image/jpeg"
                text = caption if caption else "សូមជួយពិនិត្យ និងវិភាគរូបភាពកម្រិតច្បាស់នេះឱ្យបានលម្អិត ផ្ចិតផ្ចង់ ត្រឹមត្រូវ និងមានវិជ្ជាជីវៈខ្ពស់បំផុត។"
            elif mime.startswith("video/") or fname.endswith((".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".3gp")):
                video_bytes = file_data
                video_mime = mime if mime.startswith("video/") else "video/mp4"
                text = caption if caption else "សូមជួយពិនិត្យ និងវិភាគឯកសារវីដេអូនេះឱ្យបានលម្អិត ផ្ចិតផ្ចង់ ត្រឹមត្រូវ និងមានវិជ្ជាជីវៈខ្ពស់បំផុត។"
            elif mime.startswith("audio/") or fname.endswith((".mp3", ".ogg", ".wav", ".m4a", ".aac", ".flac")):
                audio_bytes = file_data
                audio_mime = mime if mime.startswith("audio/") else "audio/mpeg"
                text = caption if caption else "សូមស្តាប់ឯកសារសម្លេងនេះដោយយកចិត្តទុកដាក់ និងឆ្លើយតបឱ្យបានតិច ចំគោលដៅ ត្រូវសំណួរ ហើយខ្លី ផ្អែមល្ហែមបំផុត។"
            elif mime == "application/pdf" or fname.endswith(".pdf"):
                doc_bytes = file_data
                doc_mime = "application/pdf"
                text = caption if caption else "សូមជួយពិនិត្យ និងវិភាគឯកសារ PDF នេះឱ្យបានលម្អិត ផ្ចិតផ្ចង់ ត្រឹមត្រូវ និងមានវិជ្ជាជីវៈខ្ពស់បំផុត។"
            else:
                doc_bytes = file_data
                doc_mime = mime or "application/octet-stream"
                text = caption if caption else f"សូមជួយពិនិត្យឯកសារ {doc.file_name} នេះឱ្យបានលម្អិត ផ្ចិតផ្ចង់ និងត្រឹមត្រូវបំផុត។"
        except Exception as d_err:
            logger.warning(f"Error downloading document: {d_err}")
    else:
        text = (update.message.text or "").strip()

    if not text and not has_photo and not has_voice and not has_audio and not has_video and not has_document:
        return

    # Error shield: check if Telegram media failed to download
    salutation = "មេ" if is_owner_user(update.effective_user) else "បង"
    if has_photo and not photo_bytes:
        await update.message.reply_text(f"សូមអភ័យទោសចាស{salutation}! ការទាញយករូបភាពពី Telegram មានការរអាក់រអួលបន្តិច សូម{salutation}ជួយផ្ញើម្តងទៀតណា៎! 🥰🌸")
        return
    if has_video and not video_bytes and (vid.file_size and vid.file_size <= 20 * 1024 * 1024):
        await update.message.reply_text(f"សូមអភ័យទោសចាស{salutation}! ការទាញយកវីដេអូពី Telegram មានការរអាក់រអួលបន្តិច សូម{salutation}ជួយផ្ញើម្តងទៀតណា៎! 🥰🌸")
        return
    if (has_voice or has_audio) and not audio_bytes:
        await update.message.reply_text(f"សូមអភ័យទោសចាស{salutation}! ការទាញយកសារសំឡេងពី Telegram មានការរអាក់រអួលបន្តិច សូម{salutation}ជួយផ្ញើម្តងទៀតណា៎! 🥰🌸")
        return

    chat_type = update.effective_chat.type
    bot_username = context.bot.username.lower() if context.bot.username else "chakriya_assistant_bot"

    if chat_type in ["group", "supergroup"]:
        text = text.replace(f"@{bot_username}", "").replace(f"@{bot_username.upper()}", "").strip()
        if not text and not has_photo and not has_voice and not has_audio and not has_video and not has_document:
            text = "សួស្តី ចរិយា"

    # Slide generation intent detection
    slide_intent_patterns = [
        "ធ្វើស្លាយអំពី", "សុំស្លាយអំពី", "បង្កើតស្លាយអំពី", "រៀបចំស្លាយអំពី",
        "ធ្វើស្លាយស្ដីពី", "សុំស្លាយស្ដីពី", "បង្កើតស្លាយស្ដីពី",
        "ជួយធ្វើស្លាយ", "ធ្វើស្លាយឱ្យ", "ធ្វើស្លាយឲ្យ", "ធ្វើស្លាយជូន", "ធ្វើស្លាយ",
        "ធ្វើ powerpoint", "បង្កើត powerpoint", "ធ្វើ ppt", "បង្កើត ppt"
    ]
    text_clean = text.lower().strip()
    is_asking_ability_only = any(q in text_clean for q in ["បានអត់", "បានទេ", "ចេះធ្វើ", "អាចធ្វើ"]) and not any(p in text_clean for p in ["អំពី", "ស្ដីពី", "ពី", "សំរាប់", "សម្រាប់"])
    wants_slide_generation = any(p in text_clean for p in slide_intent_patterns) and not is_asking_ability_only

    if wants_slide_generation and not (has_photo or has_video or has_audio or has_voice or has_document):
        topic = text
        for p in slide_intent_patterns:
            if p in topic:
                parts = topic.split(p, 1)
                if len(parts) > 1 and parts[1].strip():
                    topic = parts[1].strip()
                    break
        await handle_slide_generation_request(update, context, topic)
        return

    chat_id = update.effective_chat.id
    user = update.effective_user
    user_info = get_user_identity_info(user, text)

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
            video_mime,
            doc_bytes,
            doc_mime,
            photo_mime
        )
        formatted_reply = clean_text_formatting(reply)
        if user_info.get("just_identified"):
            formatted_reply = f"ចាស{user_info['salutation']}! ចរិយាបានកត់ត្រា និងចងចាំអត្តសញ្ញាណរបស់{user_info['salutation']}ក្នុងប្រព័ន្ធរួចរាល់ហើយណា៎! 🥰🌸\n\n" + formatted_reply
        await safe_send_reply(update, context, formatted_reply)

        # Voice Reply trigger:
        # បទបញ្ជាដាច់ខាតរបស់មេ៖ សរសេរអក្សរឆ្លើយជាអក្សរ សួរជាសំឡេងឆ្លើយជាសំឡេង!
        # លុះត្រាតែអ្នកសរសេរអក្សរសរសេរថា "សូមនិយាយជាសំឡេង" ទើបឆ្លើយជាសំឡេង បើមិនដូច្នោះទេ ហាមនិយាយជាសំឡេងឡើយ!
        incoming_is_voice = bool(has_voice or has_audio)
        explicit_voice_requests = [
            "សូមនិយាយជាសំឡេង", "សូមនិយាយជាសំលេង",
            "និយាយជាសំឡេង", "និយាយជាសំលេង",
            "ឆ្លើយជាសំឡេង", "ឆ្លើយជាសំលេង",
            "សូមឆ្លើយជាសំឡេង", "សូមឆ្លើយជាសំលេង",
            "voice note", "send voice"
        ]
        text_lower = text.lower()
        user_explicitly_asked_voice = any(phrase in text_lower for phrase in explicit_voice_requests)
        wants_voice = incoming_is_voice or user_explicitly_asked_voice

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
                elif has_document:
                    report_action = f"📁 បានផ្ញើឯកសារ ({update.message.document.file_name or 'Document'}) មកពិនិត្យ"
                else:
                    report_action = f"💬 បានឆាតសួរថា៖ {text}"

                report_to_boss = (
                    "🔔 ដំណឹងរាយការណ៍ជូនមេ (Team Activity)៖\n\n"
                    f"👤 សមាជិក៖ {user_name}\n"
                    f"{report_action}\n\n"
                    f"🌸 ចម្លើយរបស់ចរិយា៖\n{formatted_reply}"
                )
                try:
                    boss_text = clean_text_formatting(report_to_boss)
                    if len(boss_text) > 3800:
                        boss_text = boss_text[:3800] + "\n...(សារវែង ចរិយាសូមកាត់សង្ខេបត្រឹមនេះណា៎មេ)"
                    await context.bot.send_message(chat_id=int(owner_id), text=boss_text)
                except Exception as notify_err:
                    logger.warning(f"Could not forward team activity to boss: {notify_err}")
    except Exception as e:
        logger.error(f"Error handling message: {e}")
    finally:
        typing_task.cancel()

async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catch-all unhandled error handler to prevent bot polling loop crashes."""
    logger.error("Exception in update handler:", exc_info=context.error)
    try:
        if isinstance(update, Update) and update.effective_chat:
            salutation = "មេ" if update.effective_user and is_owner_user(update.effective_user) else "បង"
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"សូមអភ័យទោសចាស{salutation}! ប្រព័ន្ធជួបបញ្ហាបច្ចេកទេសបន្តិចបន្តួច តែចរិយាបានដំណើរការឡើងវិញជាធម្មតាហើយណា៎! {salutation}អាចសួរម្តងទៀតបានចាស! 🥰🌸"
            )
    except Exception as fallback_err:
        logger.error(f"Global error handler fallback failed: {fallback_err}")

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
    print("  Chakriya AI Bot (v9.0 Supreme Peak Evolution) Starting...")
    print("-----------------------------------------------------------------------------------------")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_error_handler(global_error_handler)
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("report", sales_command))
    app.add_handler(CommandHandler("sales", sales_command))
    app.add_handler(CommandHandler("slide", slide_command))
    app.add_handler(CommandHandler("slides", slide_command))
    app.add_handler(CommandHandler("ppt", slide_command))
    app.add_handler(CommandHandler("powerpoint", slide_command))
    app.add_handler(CommandHandler("memory", memory_command))
    app.add_handler(CommandHandler("clear_memory", clear_memory_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("reset", clear_command))
    app.add_handler(CommandHandler("whoami", whoami_command))
    app.add_handler(CommandHandler("me", whoami_command))
    app.add_handler(CommandHandler("id", whoami_command))
    app.add_handler(CommandHandler("team", team_command))
    app.add_handler(CommandHandler("set_team", set_team_command))
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO | filters.VOICE | filters.AUDIO | filters.VIDEO | filters.VIDEO_NOTE | filters.Document.ALL) & ~filters.COMMAND, handle_message))
    print("Bot is ready with Supreme Peak Intelligence! Waiting for messages...")
    app.run_polling()

if __name__ == "__main__":
    main()
