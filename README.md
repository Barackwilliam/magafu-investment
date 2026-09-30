# Magafu Investment: Mfumo wa Mikopo

Django + PostgreSQL (Supabase) + Render.

## Kuanza (local)
```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py setup_magafu        # tawi la kwanza + aina ya mkopo ya mfano
python manage.py createsuperuser     # huyu atakuwa admin wa mfumo
python manage.py runserver
```
Fungua http://127.0.0.1:8000 na uingie. Superuser anatambuliwa kama Admin moja kwa moja.
Bila `DATABASE_URL`, mfumo unatumia SQLite.

Kujaribu na database ya Supabase kutoka kompyuta yako: nakili `.env.example` kuwa `.env`, weka
`DATABASE_URL` ya Session pooler na `DEBUG=True`. Faili la `.env` halipandishwi GitHub.

**VS Code:** fungua folda, chagua interpreter ya `venv` (Ctrl+Shift+P → *Python: Select Interpreter*),
kisha bonyeza **F5** → *Magafu: runserver*.

## Kuunganisha Supabase

1. Fungua [supabase.com](https://supabase.com) → **New project**. Chagua region iliyo karibu na Render
   (mfano **Frankfurt / eu-central-1**) na hifadhi **Database password** mahali salama.
2. Project ikiwa tayari: bonyeza **Connect** juu ya ukurasa.
3. Chagua **Session pooler** (si "Direct connection"). Render haina IPv6, na Direct connection ya
   Supabase inatumia IPv6 tu, kwa hiyo haitaunganika.
4. Nakili URL. Inafanana na hii:
   ```
   postgresql://postgres.abcdefghijkl:[YOUR-PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:5432/postgres
   ```
   Badilisha `[YOUR-PASSWORD]` kwa password yako (bila mabano `[ ]`). Kama password ina alama
   kama `@ # / ?`, ibadilishe kwanza au i-encode (`@` → `%40`, `#` → `%23`).
   Tumia port **5432** (Session pooler), si 6543.

Hii ndiyo `DATABASE_URL`. Hakuna haja ya kuunda table kwenye Supabase: `migrate` inaziunda wakati wa deploy.

## Kupeleka Render

**Njia rahisi (Blueprint):**
1. [dashboard.render.com](https://dashboard.render.com) → **New +** → **Blueprint** → chagua repo hii.
2. Render itasoma `render.yaml` na kukuuliza `DATABASE_URL` (weka ile ya Supabase hapo juu),
   `COMPANY_PHONE`, na funguo za Beem (unaweza kuziacha wazi kwa sasa).
   `SECRET_KEY` inatengenezwa na Render yenyewe.
3. Bonyeza **Apply**. Build inaendesha `build.sh`: install, collectstatic, migrate, setup_magafu.
4. Deploy ikimaliza, fungua tab ya **Shell** ya service na uendeshe:
   ```bash
   python manage.py createsuperuser
   ```
   Huyu ndiye Admin wa mfumo. Kisha fungua `https://magafu.onrender.com` (au jina Render lililokupa).

**Njia ya mkono (bila Blueprint):** New + → **Web Service** → repo hii, Runtime **Python**,
Build `bash build.sh`, Start `gunicorn config.wsgi:application`, kisha weka environment variables
kutoka `.env.example` (`DATABASE_URL`, `SECRET_KEY` ndefu ya siri, `DEBUG=False`, `PYTHON_VERSION=3.12.7`).
`ALLOWED_HOSTS` na `CSRF_TRUSTED_ORIGINS` za `*.onrender.com` zinawekwa moja kwa moja; ziweke tu
ukiongeza domain yako mwenyewe.

**Kumbuka kuhusu mpango wa bure (free):** service inalala ikikaa dakika 15 bila mtu, na ombi la kwanza
baada ya hapo linachukua karibu dakika 1. Kwa kazi ya kila siku ya ofisi, mpango wa **Starter** unafaa zaidi.

**Cron jobs (hiari, zinalipiwa Render):** New + → **Cron Job**, repo hii, Build `pip install -r requirements.txt`,
ratiba `0 4 * * *` (UTC = saa 1 asubuhi EAT), `DATABASE_URL` na `SECRET_KEY` zile zile:
- `python manage.py apply_penalties`
- `python manage.py send_reminders`

Bila cron, vikumbusho vinaweza kutumwa kwa kitufe ndani ya mfumo.

**Kama deploy ikishindwa:**
- `connection ... Network is unreachable` → umetumia Direct connection. Tumia **Session pooler**.
- `password authentication failed` → password si sahihi, au user si `postgres.<project-ref>`.
- `Bad Request (400)` → unatumia domain yako; iongeze kwenye `ALLOWED_HOSTS` na `CSRF_TRUSTED_ORIGINS`.

## Muonekano
- Rangi za nembo (nyeusi na dhahabu), mwanga na giza (kitufe cha mwezi juu; kinakumbukwa kwenye kifaa).
- Simu kwanza: menyu ya chini, kitufe cha dhahabu "+" cha vitendo vya haraka, majedwali yanageuka kadi.
- Tafuta popote: jina, simu (hata +255...) au namba ya mkopo kama MG00012. Kwenye kompyuta bonyeza `/`.
- Inaweza kuwekwa kwenye simu kama app: fungua kwenye Chrome, kisha "Add to Home screen".
- Chart.js iko ndani ya `static/vendor/` (haitegemei CDN).


| Kazi | Afisa | Meneja | Admin |
|---|---|---|---|
| Kusajili wateja, kuomba mkopo, kupokea malipo, kurekodi matumizi | ✓ | ✓ | ✓ |
| Kuthibitisha, kukataa na kutoa mkopo, kuweka faini, kufuta muamala | | ✓ | ✓ |
| Kufuta mkopo kwenye madeni, aina za mikopo, matawi, watumiaji, ripoti ya matawi | | | ✓ |

Afisa na meneja wanaona tawi lao tu. Admin anaona yote na anaweza kuchuja kwa tawi.

## Mtiririko wa mkopo
Ombi (PENDING) → Imethibitishwa (APPROVED) → Imetolewa, anadaiwa (ACTIVE) → Amemaliza (COMPLETED)
Au: Imekataliwa (REJECTED), Imefutwa (WRITTEN_OFF). "Nje ya mkataba" = ACTIVE na tarehe ya kumaliza imepita.

## Kanuni muhimu za hesabu
- Deni halihifadhiwi kwa mkono: `deni = jumla ya kulipa + faini − marejesho`.
- Kila mkopo unahifadhi nakala ya riba, muda na aina ya marejesho siku ya ombi. Kubadilisha aina ya mkopo hakubadilishi mikopo ya zamani.
- Malipo yote yanapita `loans/services.py` (transaction + row lock), kwa hiyo malipo hayawezi kuzidi deni hata watu wawili wakilipa kwa wakati mmoja.
- Mteja mmoja anaweza kuwa na mkopo mmoja tu ambao haujaisha.
- Faini ya moja kwa moja (`penalty_per_day`) inawekwa mara moja tu kwa siku.
- "Salio la mkononi" = marejesho + ada + pesa zilizoongezwa − mikopo iliyotolewa − matumizi − benki.

## SMS (Beem Africa)
Weka `SMS_ENABLED=True`, `BEEM_API_KEY`, `BEEM_SECRET_KEY`, `SMS_SENDER_ID` (sender ID iliyoidhinishwa).
Zikiwa zimezimwa, SMS zinarekodiwa kwenye kumbukumbu bila kutumwa, nzuri kwa kujaribu.
SMS zinatumwa: mkopo ukitolewa, malipo yakipokelewa (`SMS_ON_PAYMENT`), na vikumbusho (kitufe au cron).

## Django admin
Iko kwenye `/admin/` (badilisha kwa `ADMIN_URL`). Ni kwa developer tu.

## Tests
```bash
python manage.py test loans
```

## Muundo
```
config/     settings, urls
core/       matawi, dashboard, utils (roles, scoping), setup_magafu
accounts/   watumiaji, login, roles
customers/  wateja na wadhamini
loans/      aina za mikopo, mikopo, marejesho, faini, services.py, statement
finance/    daftari la fedha (matumizi, ada, benki, pesa zilizoongezwa)
reports/    ripoti ya siku, makusanyo, mikopo iliyotolewa, madeni sugu, matawi (+ CSV)
sms/        Beem Africa, kumbukumbu, vikumbusho
```
