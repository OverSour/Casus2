import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st
import kagglehub
import plotly.graph_objects as go



@st.cache_data
def laad_data():
    path_run = kagglehub.dataset_download(
        "ajitjadhav1/strava-running-activity-data"
    )
    df_run = pd.read_excel(path_run + "/Strava Running Data.xlsx")

    # Strava Data
    path_all = kagglehub.dataset_download(
        "jairusmartinez/strava-activity-data"
    )
    df_all = pd.read_csv(path_all + "/strava_data.csv")

    # Strava Full Data
    path_3 = kagglehub.dataset_download(
        "purpleyupi/strava-data"
    )
    df_3 = pd.read_csv(path_3 + "/strava_full_data.csv")
    print("Beide datasets zijn succesvol en compact ingeladen!")

    # Holidays data  
    path_holidays = kagglehub.dataset_download(
        "anasrazy/global-national-and-observance-holidays-dataset"
    )

    df_holidays = pd.read_csv(
        path_holidays + "/holidays.csv"
    )
    return df_run, df_all, df_3, df_holidays

df_run, df_all, df_3, df_holidays = laad_data()

# de kolommen die behouden moeten worden in de opgeschoonde dataframe
df_run['date'] = df_run['start_date_local']
df_3['date'] = df_3['start_date_local']
df_3['sport_type'] = df_3['type']
kolommen_all = ['date', 'distance', 'moving_time', 'elapsed_time', 'total_elevation_gain', 'sport_type', 'achievement_count', 'average_speed', 'average_watts', 'weighted_average_watts', 'kilojoules', 'average_heartrate']
kolommen_run = ['date', 'distance', 'moving_time','elapsed_time', 'total_elevation_gain','sport_type', 'achievement_count','kudos_count', 'average_speed', 'max_speed']
kolommen_df3 = ['date', 'distance', 'moving_time', 'elapsed_time', 'total_elevation_gain','sport_type','kudos_count','average_speed','max_speed', 'average_heartrate','max_heartrate']

# opgeschoonde dataframes
df_all_clean = df_all[kolommen_all].copy()
df_run_clean = df_run[kolommen_run].copy()
df_3_clean = df_3[kolommen_df3].copy()

# zorgt ervoor dat de data naar m en km/h omzet kunnen worden door kommas met punten te veranderen want python begrijpt geen kommas
numerieke_kolommen = ['distance', 'total_elevation_gain', 'average_speed', 'max_speed']
numerieke_kolommen_df3 = ['distance', 'average_speed', 'max_speed']

# Vervang komma's door punten en zet om naar getallen voor df_run
for kolom in numerieke_kolommen:
    df_run_clean[kolom] = pd.to_numeric(
        df_run_clean[kolom].astype(str).str.replace(',', '.', regex=False),
        errors='coerce'
    )

# Vervang komma's door punten en zet om naar getallen voor df_3
for kolom in numerieke_kolommen_df3:
    df_3_clean[kolom] = pd.to_numeric(
        df_3_clean[kolom].astype(str).str.replace(',', '.', regex=False),
        errors='coerce'
    )

# hier wordt de data van running omgezet naar km en km/h zodat ze overeenkomen met de data van df_all_clean
df_run_clean[['distance']] /= 1000
df_run_clean[['moving_time', 'elapsed_time']] /= 60
df_run_clean[['average_speed', 'max_speed']] *= 3.6
df_run_clean['date'] = pd.to_datetime(df_run_clean['date'])

# Reken de waarden direct om naar km en km/h
df_3_clean['distance'] /= 1000
df_3_clean[['average_speed', 'max_speed']] *= 3.6
df_3_clean['date'] = pd.to_datetime(df_3_clean['date'])

df_totaal = pd.concat([df_all_clean, df_run_clean, df_3_clean], ignore_index=True)
df_totaal = df_totaal.drop_duplicates(subset=["date"], keep="first")
df_totaal = df_totaal.reset_index(drop=True)

def zet_om_naar_minuten(val):
    val_str = (str(val).strip())
    # Controleert of de cel leeg is of de tekst 'nan' bevat.
    if (not val_str or val_str.lower() in ["nan", "none", "<na>"]    ):  
        return np.nan
    totale_minuten = 0.0
    # Als er "days" of "day" in de tekst staat (bijv. "2 days, 6:26:01")
    if 'day' in val_str:
        dag_deel, tijd_deel = val_str.split(',') # Splits op de komma: ['2 days', ' 6:26:01']
        aantal_dagen = int([s for s in dag_deel.split() if s.isdigit()][0]) # Haal het getal uit '2 days'
        totale_minuten += aantal_dagen * 24 * 60 # Reken de dagen om naar minuten (2 * 1440)
        val_str = tijd_deel.strip() # Houd alleen het tijddeel over ("6:26:01") voor de volgende stappen
        
    if ':' in val_str:
        parts = val_str.split(':')
        if len(parts) == 3:   # H:MM:SS -> omrekenen naar minuten
            return int(parts[0]) * 60 + int(parts[1]) + int(parts[2]) / 60
        elif len(parts) == 2: # MM:SS -> omrekenen naar minuten
            return int(parts[0]) + int(parts[1]) / 60
            
    # Als het al een getal is (zoals 60.27), vervang komma's en maak er een float van
    try:
        return float(val_str.replace(',', '.'))
    except ValueError:
        return np.nan

# Pas de functie toe op beide tijdskolommen
df_totaal["moving_time"] = df_totaal["moving_time"].apply(zet_om_naar_minuten)
df_totaal["elapsed_time"] = df_totaal["elapsed_time"].apply(zet_om_naar_minuten)

# Voer nu de efficiëntie-berekening uit
df_totaal["efficiency_rate"] = (df_totaal["moving_time"] / df_totaal["elapsed_time"].replace(0, np.nan)) * 100

# Vul eventuele lege waarden (NaN) op met 0
df_totaal["efficiency_rate"] = df_totaal["efficiency_rate"].fillna(0)

# extra kolommen toevoegen met data die nuttig kan zijn
# Bereken hoeveel hoogtemeters je gemiddeld per kilometer maakt
df_totaal["meters_klimmen_per_km"] = (df_totaal["total_elevation_gain"] / df_totaal["distance"])

# Zorg dat date een echte datetime is
df_totaal["date"] = pd.to_datetime(df_totaal["date"], utc=True)

# Jaar, Maand en dag opvragen
df_totaal['jaar'] = df_totaal['date'].dt.year
df_totaal['maand'] = df_totaal['date'].dt.month
df_totaal['dag_van_de_week'] = df_totaal['date'].dt.day_name()

# 2. Weekend-indicator (bool: True of False)
df_totaal["is_weekend"] = df_totaal["date"].dt.weekday >= 5


# Voer nu de efficiëntie-berekening uit
df_totaal["efficiency_rate"] = (df_totaal["moving_time"] / df_totaal["elapsed_time"].replace(0, np.nan)) * 100

# Vul eventuele lege waarden (NaN) op met 0
df_totaal["efficiency_rate"] = df_totaal["efficiency_rate"].fillna(0)

# 1. Zet moving_time en elapsed_time om naar echte getallen (tekst/komma's worden platgeslagen)
df_totaal["moving_time"] = pd.to_numeric(
    df_totaal["moving_time"].astype(str).str.replace(",", ".", regex=False),
    errors="coerce",
)
df_totaal["elapsed_time"] = pd.to_numeric(
    df_totaal["elapsed_time"].astype(str).str.replace(",", ".", regex=False),
    errors="coerce",
)

# 2. Voer nu de berekening veilig uit (inclusief de fix voor de nullen)
df_totaal["efficiency_rate"] = (
    df_totaal["moving_time"] / df_totaal["elapsed_time"].replace(0, np.nan)
) * 100

# 3. Vul eventuele lege waarden (NaN) netjes op met 0
df_totaal["efficiency_rate"] = df_totaal["efficiency_rate"].fillna(0)

#verdeelt de type sporten onder in groepen
voet_sporten = ['Run', 'Walk', "Hike"]
fiets_sporten = ['Ride', 'VirtualRide']
water_sport = ['Swim']
bekende_sporten = voet_sporten + fiets_sporten + water_sport

#maakt apparte dataframes aan voor de groepen en de rest die over blijft
df_voet = df_totaal[df_totaal['sport_type'].isin(voet_sporten)]
df_fiets = df_totaal[df_totaal['sport_type'].isin(fiets_sporten)]
df_water = df_totaal[df_totaal['sport_type'].isin(water_sport)]
df_overig = df_totaal[~df_totaal['sport_type'].isin(bekende_sporten)]

# Tel per feestdag in hoeveel verschillende landen deze voorkomt
aantal_landen = df_holidays.groupby("name")["country"].nunique()

# Behoud alleen feestdagen die in minimaal 50 landen voorkomen
belangrijke_feestdagen = aantal_landen[
    aantal_landen >= 50
].index

df_holidays = df_holidays[
    df_holidays["name"].isin(belangrijke_feestdagen)
].copy()

# Verwijder seizoensgebonden dagen die niet feestdagen zijn
geen_feestdagen = [
    "March Equinox",
    "June Solstice",
    "September Equinox",
    "December Solstice"
]

df_holidays = df_holidays[
    ~df_holidays["name"].isin(geen_feestdagen)
].copy()

# Verwijder dagen die tussen landen verschillen kwa datum
verwijderen = [
    "Mother's Day",
    "Father's Day",
    "Labor Day",
    "Independence Day",
    "Feast of the Sacrifice",
    "Festival of Breaking the Fast",
    "All Saints' Day",
    "Birth of the Prophet"
]

df_holidays = df_holidays[
    ~df_holidays["name"].isin(verwijderen)
].copy()

# Zorg dat beide datums hetzelfde formaat hebben
df_totaal["date_key"] = pd.to_datetime(df_totaal["date"]).dt.date
df_holidays["date_key"] = pd.to_datetime(df_holidays["date"]).dt.date

# Hou alleen unieke feestdagen per datum
df_holidays_unique = df_holidays[["date_key", "name"]].drop_duplicates()

# Merge de feestdagen met de Strava-data
df_totaal = pd.merge(
    df_totaal,
    df_holidays_unique,
    on="date_key",
    how="left",
    indicator=True
)

# True als de datum een feestdag is
df_totaal["is_holiday"] = df_totaal["_merge"] == "both"

# Verwijder de tijdelijke merge-kolom
df_totaal = df_totaal.drop(columns="_merge")

df_totaal.loc[
    df_totaal['sport_type'].isin(voet_sporten),
    'sport_type'
] = 'Voet'

df_totaal.loc[
    df_totaal['sport_type'].isin(fiets_sporten),
    'sport_type'
] = 'Fiets'

df_totaal.loc[
    df_totaal['sport_type'].isin(water_sport),
    'sport_type'
] = 'Water'

df_totaal.loc[
    ~df_totaal['sport_type'].isin(['Voet', 'Fiets', 'Water']),
    'sport_type'
] = 'Overig'

df_totaal = df_totaal[df_totaal["date"].dt.year != 2010]

KLEUR_SPORT ={
    'Voet': '#E69F00',    
    'Fiets': '#CC79A7',   
    'Water': '#0072B2',   
    'Overig': '#009E73'   
}
 
# Zorg voor een nette chronologische volgorde van de dagen op de X-as
DAGEN_VOLGORDE = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
 
MAAND_NAMEN_EN = {
    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December",
}

df = df_totaal
 
 
def datum_slider(df):
    """Slider met twee handvatten om een datumbereik te kiezen."""
    eerste_datum = df["date"].min().date()
    laatste_datum = df["date"].max().date()
 
    return st.sidebar.slider(
        "Kies een periode",
        min_value=eerste_datum,
        max_value=laatste_datum,
        value=(eerste_datum, laatste_datum),  # een tuple maakt er een range-slider van
        format="DD-MM-YYYY",
    )
 
 
def filter_op_datum(df, begin, eind):
    """Houdt alleen de workouts tussen begin en eind (inclusief) over."""
    datums = df["date"].dt.date
    return df[(datums >= begin) & (datums <= eind)]
 
 
# ---------------------------------------------------------------
# Grafieken
# ---------------------------------------------------------------
 
 
def grafiek_per_weekdag(df):
    return px.bar(
        df,
        x="dag_van_de_week",
        color="sport_type",
        color_discrete_map=KLEUR_SPORT,
        title="Aantal trainingen per dag van de week",
        category_orders={"dag_van_de_week": DAGEN_VOLGORDE},
        labels={"dag_van_de_week": "Dag van de week", "count": "Aantal trainingen"},
        barmode="stack",
    )
 
 
def grafiek_per_maand(df):
    # Groepeer de data per maand en per sporttype
    df_maand = df.groupby(["maand", "sport_type"]).size().reset_index(name="aantal")
    df_maand["maand_naam"] = df_maand["maand"].map(MAAND_NAMEN_EN)
 
    return px.bar(
        df_maand,
        x="maand_naam",
        y="aantal",
        color="sport_type",
        color_discrete_map=KLEUR_SPORT,
        title="Sport Choice Throughout the Year",
        labels={"maand_naam": "Month", "aantal": "Number of Workouts", "sport_type": "Sport Type"},
        category_orders={"maand_naam": list(MAAND_NAMEN_EN.values())},  # Jan t/m Dec
        barmode="group",
    )
 
 
def grafiek_conditie(df):
    # Filter data die een geldige hartslag en snelheid heeft
    df_conditie = df[(df["average_heartrate"] > 0) & (df["average_speed"] > 0)]
 
    return px.scatter(
        df_conditie,
        x="average_speed",
        y="average_heartrate",
        color="sport_type",
        color_discrete_map=KLEUR_SPORT,
        title="Snelheid vs. Hartslag (Conditietest)",
        labels={"average_speed": "Gemiddelde snelheid (km/u)", "average_heartrate": "Gemiddelde Hartslag (bpm)"},
    )
 








def grafiek_gemiddelde_per_tijd(df):
    keuze = st.selectbox(
        "Bekijk:",
        ["Jaar", "Maand", "Weekdag", "Dagdeel", "Feestdag"]
    )

    # ---------------------------------------------------------
    # JAAR
    # ---------------------------------------------------------
    if keuze == "Jaar":

        telling = (
            df
            .groupby(["jaar", "sport_type"])
            .size()
            .reset_index(name="aantal")
        )

        fig = px.bar(
            telling,
            x="jaar",
            y="aantal",
            color="sport_type",
            color_discrete_map=KLEUR_SPORT,
            title="Aantal workouts per jaar",
            labels={
                "jaar": "Jaar",
                "aantal": "Aantal workouts",
                "sport_type": "Sport Type"
            },
            barmode="stack"
        )

        alle_jaren = sorted(df["jaar"].unique())

        fig.update_xaxes(
            tickmode="array",
            tickvals=alle_jaren,
            ticktext=[str(jaar) for jaar in alle_jaren]
        )

        return fig, keuze

    # ---------------------------------------------------------
    # MAAND
    # ---------------------------------------------------------
    elif keuze == "Maand":

        telling = (
            df
            .groupby(["jaar", "maand", "sport_type"])
            .size()
            .reset_index(name="aantal")
        )

        telling = (
            telling
            .groupby(["maand", "sport_type"])["aantal"]
            .mean()
            .reset_index()
        )

        telling["maand_naam"] = telling["maand"].map(MAAND_NAMEN_EN)

        return px.bar(
            telling,
            x="maand_naam",
            y="aantal",
            color="sport_type",
            color_discrete_map=KLEUR_SPORT,
            title="Gemiddeld aantal workouts per maand",
            labels={
                "maand_naam": "Maand",
                "aantal": "Gemiddeld aantal workouts",
                "sport_type": "Sport Type"
            },
            category_orders={
                "maand_naam": list(MAAND_NAMEN_EN.values())
            },
            barmode="stack"
        ), keuze

    # ---------------------------------------------------------
    # WEEKDAG
    # ---------------------------------------------------------
    elif keuze == "Weekdag":

        telling = (
            df
            .groupby(["jaar", "dag_van_de_week", "sport_type"])
            .size()
            .reset_index(name="aantal")
        )

        telling = (
            telling
            .groupby(["dag_van_de_week", "sport_type"])["aantal"]
            .mean()
            .reset_index()
        )

        return px.bar(
            telling,
            x="dag_van_de_week",
            y="aantal",
            color="sport_type",
            color_discrete_map=KLEUR_SPORT,
            title="Gemiddeld aantal workouts per weekdag",
            labels={
                "dag_van_de_week": "Dag van de week",
                "aantal": "Gemiddeld aantal workouts",
                "sport_type": "Sport Type"
            },
            category_orders={
                "dag_van_de_week": DAGEN_VOLGORDE
            },
            barmode="stack"
        ), keuze
    # ---------------------------------------------------------
    # DAGDEEL
    # ---------------------------------------------------------
    elif keuze == "Dagdeel":
        grenzen = [0, 6, 12, 18, 24]
        labels = ["Nacht", "Ochtend", "Middag", "Avond"]

        df = df.copy()

        df["dagdeel"] = pd.cut(
            df["date"].dt.hour,
            bins=grenzen,
            labels=labels,
            right=False
        )

        df_dagdeel = (
            df
            .groupby(["dagdeel", "sport_type"], observed=True)
            .size()
            .reset_index(name="aantal")
        )

        return px.bar(
            df_dagdeel,
            x="dagdeel",
            y="aantal",
            color="sport_type",
            color_discrete_map=KLEUR_SPORT,
            category_orders={
                "dagdeel": labels
            },
            barmode="stack",
            title="Aantal trainingen per dagdeel",
            labels={
                "dagdeel": "Dagdeel",
                "aantal": "Aantal trainingen",
                "sport_type": "Sport"
            }
        ), keuze
    # ---------------------------------------------------------
    # FEESTDAG
    # ---------------------------------------------------------
    else:

        
        df_feest = df.copy()

        normale_mask = (
            df_feest["is_holiday"].fillna(False) == False
        )

        normale_activiteiten = int(
            df_feest.loc[normale_mask].shape[0]
        )

        # Gemiddeld aantal workouts per normale dag
        normale_dag_waarde = round(
            normale_activiteiten / 365,
            1
        )

        tabel = (
            df_feest
            .assign(
                name=df_feest["name"].fillna("Normale dag")
            )
            .groupby("name")
            .size()
            .reset_index(name="aantal")
        )

        tabel["aantal"] = tabel["aantal"].astype(float)

        tabel["type"] = np.where(
            tabel["name"] == "Normale dag",
            "Normale dag",
            "Feestdag"
        )

        tabel.loc[
            tabel["name"] == "Normale dag",
            "aantal"
        ] = normale_dag_waarde

        tabel = (
            tabel
            .sort_values("aantal", ascending=True)
            .reset_index(drop=True)
        )

        fig = px.bar(
            tabel,
            x="name",
            y="aantal",
            title="Aantal workouts per feestdag vs normale dagen",
            labels={
                "name": "Dag",
                "aantal": "Gemiddeld aantal workouts"
            },
            color="type",
            color_discrete_map={
                "Normale dag": "#0072B2",
                "Feestdag": "gray",
            },
            text_auto=".1f"
        )

        fig.update_xaxes(
            categoryorder="array",
            categoryarray=tabel["name"].tolist()
        )

        return fig, keuze


# ---------------------------------------------------------------
# Pagina
# ---------------------------------------------------------------
st.title("Strava & Feestdagen")

st.markdown("""
## Inleiding

Sporten is gezond, maar de manier waarop we onze trainingen inplannen is sterk afhankelijk van onze dagelijkse routines, het weer en de seizoenen. Om te begrijpen hoe mensen hun sportgedrag structureren, onderzoekt dit rapport de exacte timing van fysieke activiteiten. Centraal staat de vraag: **"Op welk moment van het jaar, de week en de dag sporten mensen het meest, en verschilt dit per type sport?"** Aan de hand van vier datavisualisaties analyseren we patronen op het gebied van maanden, weekdagen, feestdagen en dagdelen, inclusief de specifieke sportkeuzes per moment.
""")

begin, eind = datum_slider(df_totaal)
df_gefilterd = filter_op_datum(df_totaal, begin, eind)

st.caption(f"{len(df_gefilterd)} workouts tussen {begin:%d-%m-%Y} en {eind:%d-%m-%Y}")

if df_gefilterd.empty:
    st.warning("Geen workouts in deze periode. Kies een groter bereik.")
    st.stop()

with st.expander("Bekijk de dataset"):
    st.dataframe(df_gefilterd)

st.plotly_chart(grafiek_conditie(df_gefilterd), width="stretch")




fig, keuze = grafiek_gemiddelde_per_tijd(df_gefilterd)


if keuze == "Maand":
    st.markdown("""
    ### Sportkeuze door het jaar heen (Maanden)

    De sportfrequentie is sterk seizoensgebonden, met een absolute piek in de zomermaand juli. Als we naar de specifieke sporten kijken, valt op dat hardlopen (Run) vooral in de zomermaanden populair is, met een duidelijke piek in juli en augustus. Daarnaast is er een opmerkelijke trend zichtbaar bij het buitenfietsen (*Ride*): deze activiteit stijgt vanaf de maand juli tot en met de maand november, waarna het in de winter weer inzakt. Zwemmen (*Swim*) blijft daarentegen het hele jaar door stabiel met een nagenoeg gelijke verdeling over de maanden. Tot slot laat binnenfietsen (*VirtualRide*) een piek zien die vooral tussen april en augustus ligt, wat opvallend is voor een binnensport.
    """)
elif keuze == "Weekdag":
    st.markdown("""
    ### Aantal trainingen per dag van de week

    De sportfrequentie laat een heel dynamisch verloop zien over de week. Maandag start opvallend rustig met relatief weinig trainingen, waarna de activiteit op dinsdag direct naar de piek van de week schiet. Na deze dinsdagpiek neemt het aantal trainingen geleidelijk af richting de vrijdag, wat de rustigste doordeweekse dag is. In het weekend stijgt het aantal trainingen juist weer, waarbij zaterdag en zondag flink actiever zijn dan de vrijdag. Wel is er tijdens deze weekendstijging een duidelijke verschuiving in het type sport zichtbaar: het aandeel VirtualRide (binnenfietsen) neemt sterk af, terwijl de categorie Ride (buitenfietsen) juist groter wordt.
    """)
elif keuze == "Dagdeel":
    st.markdown("""
    ### Sporten per dagdeel

    De ochtend (06:00 - 12:00 uur) is over het algemeen het populairste sportmoment van de dag, direct gevolgd door de middag, terwijl de avond- en nachturen het minst populair zijn. Deze timing bepaalt echter sterk de specifieke sportkeuze. Activiteiten die buiten plaatsvinden, zoals buitenfietsen (Ride) en wandelen (Walk), kennen hun absolute piek in de vroege ochtenduren wanneer mensen graag profiteren van het daglicht. Zodra men echter binnen gaat sporten op een interactieve trainer (VirtualRide), verschuift de absolute piek juist naar de middag (12:00 - 18:00 uur).
    """)
elif keuze == "Feestdag":
    st.markdown("""
    ### Sporten op feestdagen

    Op een gemiddelde, normale dag worden er ruim 8 workouts geregistreerd (blauwe balk). Feestdagen die traditioneel in het teken staan van familie of feesten, zoals New Year's Eve (1), Christmas Day (8) en Christmas Eve (8), scoren lager of gelijk aan dit gemiddelde. Officiële feestdagen of vrije dagen die minder strikte verplichtingen kennen, zoals Assumption of Mary (10) en Pentecost Monday (10), laten juist een stijging zien. Mensen benutten die extra vrije tijd dus vaker om te gaan sporten
    """)
    
st.plotly_chart(fig, width="stretch")

st.markdown("""
## Conclusie: Het ultieme sportmoment en de invloed op sportkeuze

Als antwoord op de hoofdvraag kan worden gesteld dat het sportgedrag van mensen sterk afhankelijk is van de kalender en de klok. Mensen sporten het meest in de **ochtend (tussen 06:00 en 12:00 uur)**, op een **dinsdag** en tijdens de **zomermaand juli**.

### De week en het jaar

De week start rustig op maandag, bereikt op dinsdag een absolute piek en neemt daarna af tot vrijdag, waarna het weekend weer een stijging laat zien. **Juli is de populairste sportmaand van het jaar.**

### Feestdagen

Dit hangt sterk af van het type feestdag. Familiegerichte dagen scoren onder het gemiddelde van een normale dag (**8,3 workouts**), met **New Year's Eve** als absoluut dieptepunt met 1 workout. Minder traditionele vrije dagen zorgen juist voor een stijging, met uitschieters tot **10 workouts** op dagen zoals **Assumption of Mary** en **Pentecost Monday**.

### Verschillen per sporttype

De timing bepaalt fundamenteel de sportkeuze. Buitenactiviteiten zoals buitenfietsen (*Ride*) en wandelen (*Walk*) worden massaal in de vroege ochtend gedaan, waarbij buitenfietsen een specifieke piek kent van ruim **400 trainingen**.

Bovendien stijgt buitenfietsen in de tweede helft van het jaar (**juli tot november**) en tijdens de weekenden. De indoorvariant (*VirtualRide*) kent daarentegen een verrassende verschuiving naar de middaguren (**12:00 - 18:00 uur**) met een piek van **357 trainingen**, en is met name populair tussen **april en augustus**.

Hardlopen is vooral een **zomersport**, met de grootste activiteit in juli en augustus, terwijl zwemmen als enige sport **het hele jaar door stabiel** blijft.
""")


st.markdown("---")

st.subheader("Gebruikte bronnen en verantwoording ")

st.markdown("""
- [Strava Activity Data](https://www.kaggle.com/datasets/jairusmartinez/strava-activity-data)
- [Strava Running Activity Data](https://www.kaggle.com/datasets/ajitjadhav1/strava-running-activity-data)
- [Strava Data](https://www.kaggle.com/datasets/purpleyupi/strava-data)
- [Global National and Observance Holidays Dataset](https://www.kaggle.com/datasets/anasrazy/global-national-and-observance-holidays-dataset)
""")

st.markdown("""
Deze bestanden zijn allemaal met behulp van `kagglehub.dataset_download()` uitgelezen.

De volgende datasets zijn samengevoegd: **strava-activity-data**, **strava-running-activity-data** en **strava-data**. Deze datasets zijn samengevoegd met behulp van `pd.concat()`. Dit is gedaan door de gegevens die overeenkwamen met elkaar te verbinden. Dit is gedaan voor de kolommen: `date`, `distance`, `moving_time`, `elapsed_time`, `total_elevation_gain`, `sport_type` en `average_speed`.

De kolommen die niet nuttig zijn voor onze visualisatie zijn verwijderd. Vervolgens zijn de kolommen **maand** en **dag van de week** toegevoegd op basis van de gegevens uit de kolom datum om de dataset bruikbaarder te maken.

De overgebleven kolommen hadden enkele problemen. Dit kwam doordat de verschillende datasets verschillende manieren hadden voor het noteren van de datum, beweegtijd, afstand en gemiddelde snelheid. Deze zijn daarom in een uniforme notatie geschreven.

Een ander probleem dat werd veroorzaakt door het combineren van de dataframes was dat sommige kolommen niet in alle datasets voorkwamen. Deze kolommen zijn wel bewaard gebleven. Voor de datasets waarin deze kolommen niet voorkwamen, zijn de rijen ingevuld met `NaN`.

Als laatste is er nog een dataset toegevoegd om te bepalen wat de feestdagen zijn. Dit is gedaan door `pd.merge()`.

### AI-verantwoording

AI is onder andere gebruikt voor het oplossen van programmeerproblemen, het controleren van code en het verbeteren van de structuur van de code. De gebruikte datasets, keuzes in de verwerking van de gegevens en de uiteindelijke visualisaties zijn door onszelf gecontroleerd en beoordeeld.
""")

