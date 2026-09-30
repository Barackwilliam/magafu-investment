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

## Kupeleka Render
1. Web Service: Build `./build.sh`, Start `gunicorn config.wsgi:application`
2. Weka environment variables kutoka `.env.example` (`DATABASE_URL` ya Supabase, `SECRET_KEY`, `DEBUG=False`)
3. Baada ya deploy ya kwanza, kwenye Shell: `python manage.py createsuperuser`
4. Cron jobs (Render Cron Job, kila asubuhi, mfano `0 4 * * *` UTC = saa 1 asubuhi EAT):
   - `python manage.py apply_penalties`
   - `python manage.py send_reminders`

## Roles
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
Iko kwenye `/mfumo-ndani/` (badilisha kwa `ADMIN_URL`). Ni kwa developer tu.

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
