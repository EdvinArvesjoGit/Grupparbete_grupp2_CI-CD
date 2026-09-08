# Arbetslogg – Grupp 2

**Projekt:** ETL-pipeline över Sveriges riksdags öppna data
**Repo:** https://github.com/EdvinArvesjoGit/Grupparbete_grupp2_CI-CD
**Kurs:** DevOps, DE25

**Deltagare:** Alexander Maximainen, Xin Gao, Dinara Minullina Filip Larsson, Edvin Arvesjö, David Färm 

---

## Arbetsfördelning

Arbetet delades i sex ansvarsområden längs dataflödet: två för inhämtning
via API, ett för transformation till stjärnschema, två för rapportering och
ett för gemensam plattform och CI/CD. Varje område hade en tydlig ägare med
egen mapp i repot, vilket gjorde att vi kunde arbeta parallellt med få
merge-konflikter. Vi kom överens om ett gemensamt datakontrakt
(`DATABASE.md`) innan kodningen startade, så att alla kunde bygga mot en
känd struktur redan från dag ett.

All kod har gått genom pull requests med kodgranskning och godkännande från
två gruppmedlemmar innan merge till `main`.

---

## Vem har gjort vad

**Alexander Maximainen – inhämtning av ledamotsdata**
Byggde extraheringen mot riksdagens personlista: hämtning via API, parsning
av ledamöter och uppdrag, samt laddning till `stg.person`,
`stg.person_uppdrag` och `stg.person_uppgift`. Ansvarade även för
DDL-skripten för dessa tabeller.

**Xin Gao – inhämtning av voteringsdata**
Byggde extraheringen av voteringar, som är projektets tyngsta datakälla med
över 900 000 rader. Konstruerade en inkrementell laddning som bara hämtar
nya voteringar vid varje körning, vilket senare blev en förutsättning för
att kunna köra pipelinen automatiskt. Migrerade också sin modul först till
gruppens gemensamma gränssnitt `run(engine, korning_id)`.

**Filip Larsson – transformation och datamodellering**
Byggde transformationen från staging till stjärnschema, inklusive
dimensionen `dw.dim_ledamot`. Ansvarade för DDL för dw-lagret och för de designbeslut som
modelleringen krävde.

**Dinara Minullina – rapportering, riksdagens sammansättning**
Byggde rapportlagret för riksdagens sammansättning, med datamodeller och
API-lager mot det färdiga stjärnschemat.

**Edvin Arvesjö – rapportering, röstningsmönster**
Byggde rapportlagret för röstningsbeteende och analys av voteringar.

**David Färm – plattform, orkestrering och CI/CD**
Satte upp projektets grundstruktur: mappstruktur, `.gitignore`,
`.env`-hantering, gemensam databasanslutning och schemaskript. Byggde
orkestreraren `run_pipeline.py` som kör alla steg i beroendeordning med
gemensamt körnings-ID och loggning till `ops.load_log`. Ansvarade för
CI-flödet i GitHub Actions med lint, formatkontroll, enhetstester och
integrationstester mot en riktig Postgres-databas, samt för det schemalagda
flödet som bygger och publicerar datalagret som en release (CD flöde).

---

## Gemensamt arbete

Datamodellen, namnkonventionerna och gränssnittet mellan modulerna togs fram
gemensamt på projektmöten. Flera av de viktigaste besluten under projektet –
bland annat att standardisera hur modulerna anropas och hur kolumntyper ska
sättas – kom ur kodgranskningar där en gruppmedlem uppmärksammade något i
någon annans kod. Samtliga i gruppen har granskat och godkänt varandras pull
requests.

**Källa: Sveriges riksdag**
