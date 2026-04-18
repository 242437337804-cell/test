import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

# Configuration de la page
st.set_page_config(
    page_title="Analyse Risque Sismique - Algérie RPA99",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Zonage sismique RPA99 complet
RPA99_ZONING = {
    'Zone III': {
        'wilayas': ['ALGER', 'BOUMERDES', 'TIPAZA', 'BLIDA', 'BEJAIA', 'TIZI OUZOU', 
                   'JIJEL', 'SKIKDA', 'ANNABA', 'EL TAREF', 'CONSTANTINE', 'MILA'],
        'coefficient_acceleration': 0.25,
        'risk_level': 'Élevé',
        'color': '#DC143C',
        'pml_factor': 0.40
    },
    'Zone IIb': {
        'wilayas': ['SETIF', 'BORDJ BOU ARRERIDJ', 'BATNA', 'KHENCHELA', 'TEBESSA',
                   'AIN DEFLA', 'CHLEF', 'MOSTAGANEM', 'RELIZANE', 'TIARET'],
        'coefficient_acceleration': 0.20,
        'risk_level': 'Moyen-Élevé',
        'color': '#FF8C00',
        'pml_factor': 0.25
    },
    'Zone IIa': {
        'wilayas': ['MEDEA', 'MSILA', 'BISKRA', 'OUARGLA', 'GHARDAIA', 'LAGHOUAT',
                   'DJELFA', 'TAMENRASSET', 'ILLIZI'],
        'coefficient_acceleration': 0.15,
        'risk_level': 'Moyen',
        'color': '#FFD700',
        'pml_factor': 0.15
    },
    'Zone I': {
        'wilayas': ['SAIDA', 'TLEMCEN', 'SIDI BEL ABBES', 'MASCARA', 'AIN TEMOUCHENT',
                   'ORAN', 'EL BAYADH', 'NAAMA'],
        'coefficient_acceleration': 0.10,
        'risk_level': 'Faible',
        'color': '#90EE90',
        'pml_factor': 0.08
    },
    'Zone 0': {
        'wilayas': ['ADRAR', 'TIMIMOUN', 'REGGANE', 'TINDOUF'],
        'coefficient_acceleration': 0.05,
        'risk_level': 'Négligeable',
        'color': '#87CEEB',
        'pml_factor': 0.03
    }
}

@st.cache_data
@st.cache_data
def load_data(uploaded_file=None):
    """Chargement et traitement des données"""
    if uploaded_file is None:
        # Charger le fichier par défaut s'il existe
        try:
            df = pd.read_excel('C:\\Users\\hadri\\Downloads\\CATNAT_2023_2025.xlsx', sheet_name=None)
            df_combined = pd.concat(df.values(), ignore_index=True)
        except FileNotFoundError:
            st.error("Fichier 'CATNAT_2023_2025.xlsx' non trouvé. Veuillez uploader un fichier.")
            return pd.DataFrame()
    else:
        # Charger le fichier uploadé
        df = pd.read_excel(uploaded_file, sheet_name=None)
        df_combined = pd.concat(df.values(), ignore_index=True)
    
    # Nettoyage
    df_combined['CAPITAL_ASSURE'] = pd.to_numeric(
        df_combined['CAPITAL_ASSURE'], errors='coerce'
    ).fillna(0)
    df_combined['PRIME_NETTE'] = pd.to_numeric(
        df_combined['PRIME_NETTE'], errors='coerce'
    ).fillna(0)
    
    # Extraction wilaya
    df_combined['WILAYA_NAME'] = df_combined['WILAYA'].apply(
        lambda x: str(x).split('-')[-1].strip() if pd.notna(x) else 'UNKNOWN'
    )
    
    return df_combined
    
def map_seismic_zone(wilaya_name):
    """Mapper une wilaya vers sa zone sismique"""
    wilaya_clean = wilaya_name.upper().strip()
    for zone, info in RPA99_ZONING.items():
        if wilaya_clean in info['wilayas']:
            return zone
    return 'Zone IIa'  # Zone par défaut

def analyze_portfolio(df):
    """Analyse complète du portefeuille"""
    if df.empty:
        return None
    
    # Mapping des zones
    df['ZONE_SISMIQUE'] = df['WILAYA_NAME'].apply(map_seismic_zone)
    
    # Ajouter les coefficients
    df['COEFF_ACCEL'] = df['ZONE_SISMIQUE'].apply(
        lambda x: RPA99_ZONING[x]['coefficient_acceleration']
    )
    df['RISK_LEVEL'] = df['ZONE_SISMIQUE'].apply(
        lambda x: RPA99_ZONING[x]['risk_level']
    )
    df['PML_FACTOR'] = df['ZONE_SISMIQUE'].apply(
        lambda x: RPA99_ZONING[x]['pml_factor']
    )
    
    # Calcul PML
    df['PML_ESTIMEE'] = df['CAPITAL_ASSURE'] * df['PML_FACTOR']
    
    # Analyse par zone
    exposure_by_zone = df.groupby('ZONE_SISMIQUE').agg({
        'CAPITAL_ASSURE': ['sum', 'count', 'mean'],
        'PRIME_NETTE': 'sum',
        'PML_ESTIMEE': 'sum'
    }).round(2)
    
    exposure_by_zone.columns = ['Capital_Total', 'Nb_Polices', 'Capital_Moyen', 
                                 'Prime_Total', 'PML_Totale']
    
    # Analyse par wilaya
    exposure_by_wilaya = df.groupby(['WILAYA_NAME', 'ZONE_SISMIQUE']).agg({
        'CAPITAL_ASSURE': 'sum',
        'NUMERO_POLICE': 'count',
        'PML_ESTIMEE': 'sum'
    }).reset_index()
    
    exposure_by_wilaya.columns = ['Wilaya', 'Zone', 'Capital_Total', 'Nb_Polices', 'PML']
    
    # Pourcentage du portefeuille
    total_capital = exposure_by_wilaya['Capital_Total'].sum()
    exposure_by_wilaya['Pct_Portefeuille'] = (
        exposure_by_wilaya['Capital_Total'] / total_capital * 100
    ).round(2)
    
    # Identification hotspots (>5% du portefeuille)
    exposure_by_wilaya['HOTSPOT'] = exposure_by_wilaya['Pct_Portefeuille'] > 5.0
    
    # Analyse par type
    exposure_by_type = df.groupby('TYPE').agg({
        'CAPITAL_ASSURE': 'sum',
        'NUMERO_POLICE': 'count',
        'PML_ESTIMEE': 'sum'
    }).reset_index()
    
    exposure_by_type.columns = ['Type', 'Capital', 'Nb_Polices', 'PML']
    
    return {
        'df': df,
        'by_zone': exposure_by_zone,
        'by_wilaya': exposure_by_wilaya,
        'by_type': exposure_by_type,
        'total_capital': total_capital,
        'total_pml': df['PML_ESTIMEE'].sum()
    }

def generate_recommendations(analysis):
    """Générer les recommandations"""
    recommendations = {'surconcentration': [], 'opportunities': [], 'alerts': []}
    
    # Surconcentrations
    hotspots = analysis['by_wilaya'][
        (analysis['by_wilaya']['HOTSPOT'] == True) & 
        (analysis['by_wilaya']['Zone'].isin(['Zone III', 'Zone IIb']))
    ]
    
    for _, row in hotspots.iterrows():
        recommendations['surconcentration'].append({
            'wilaya': row['Wilaya'],
            'zone': row['Zone'],
            'capital': row['Capital_Total'],
            'pct': row['Pct_Portefeuille'],
            'pml': row['PML'],
            'action': f"Réduire de {row['Pct_Portefeuille'] - 5:.1f}%"
        })
    
    # Opportunités (zones faibles risques sous-exposées)
    opportunities = analysis['by_wilaya'][
        (analysis['by_wilaya']['Pct_Portefeuille'] < 1.0) &
        (analysis['by_wilaya']['Zone'].isin(['Zone I', 'Zone IIa']))
    ]
    
    for _, row in opportunities.iterrows():
        recommendations['opportunities'].append({
            'wilaya': row['Wilaya'],
            'zone': row['Zone'],
            'capital': row['Capital_Total']
        })
    
    # Alertes PML
    if analysis['total_pml'] > analysis['total_capital'] * 0.20:
        recommendations['alerts'].append(
            f"PML totale élevée: {analysis['total_pml']:,.0f} DA "
            f"({analysis['total_pml']/analysis['total_capital']*100:.1f}% du capital)"
        )
    
    return recommendations

# Interface Streamlit
def main():
    st.title("🏛️ Système d'Analyse du Risque Sismique - RPA99")
    st.markdown("---")
    
    # Chargement des données
    with st.spinner('Chargement des données...'):
        df = load_data()
    
    if df.empty:
        st.error("Impossible de charger les données. Vérifiez le fichier Excel.")
        return
    
    # Analyse
    analysis = analyze_portfolio(df)
    recommendations = generate_recommendations(analysis)
    
    # Sidebar
    st.sidebar.header("📊 Filtres")
    selected_zones = st.sidebar.multiselect(
        "Zones Sismiques",
        options=list(RPA99_ZONING.keys()),
        default=list(RPA99_ZONING.keys())
    )
    
    selected_types = st.sidebar.multiselect(
        "Types de Risques",
        options=analysis['df']['TYPE'].unique(),
        default=analysis['df']['TYPE'].unique()
    )
    
    # Filtrage
    df_filtered = analysis['df'][
        (analysis['df']['ZONE_SISMIQUE'].isin(selected_zones)) &
        (analysis['df']['TYPE'].isin(selected_types))
    ]
    
    # KPIs
    st.subheader("📈 Indicateurs Clés")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💰 Capital Total Assuré",
            f"{analysis['total_capital']:,.0f} DA"
        )
    with col2:
        st.metric(
            "📋 Nombre de Polices",
            f"{len(analysis['df']):,}"
        )
    with col3:
        st.metric(
            "⚠️ PML Totale",
            f"{analysis['total_pml']:,.0f} DA",
            delta=f"{analysis['total_pml']/analysis['total_capital']*100:.2f}% du capital"
        )
    with col4:
        max_risk_zone = analysis['by_zone']['PML_Totale'].idxmax()
        st.metric("🎯 Zone la plus Critique", max_risk_zone)
    
    st.markdown("---")
    
    # Visualisations
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Exposition par Zone",
        "🗺️ Carte des Risques",
        "🔥 Points Chauds",
        "💡 Recommandations",
        "📋 Données Détaillées"
    ])
    
    with tab1:
        st.subheader("Exposition par Zone Sismique")
        
        fig = make_subplots(
            rows=2, cols=2,
            specs=[[{"type": "bar"}, {"type": "pie"}],
                   [{"type": "bar"}, {"type": "bar"}]],
            subplot_titles=(
                'Capital Assuré par Zone',
                'Répartition du Portefeuille',
                'PML par Zone',
                'Nombre de Polices'
            )
        )
        
        zones = analysis['by_zone'].index.tolist()
        colors = [RPA99_ZONING[z]['color'] for z in zones]
        
        # Capital
        fig.add_trace(
            go.Bar(x=zones, y=analysis['by_zone']['Capital_Total'],
                   marker_color=colors, name='Capital'),
            row=1, col=1
        )
        
        # Pie
        fig.add_trace(
            go.Pie(labels=zones, values=analysis['by_zone']['Capital_Total'],
                   marker_colors=colors),
            row=1, col=2
        )
        
        # PML
        fig.add_trace(
            go.Bar(x=zones, y=analysis['by_zone']['PML_Totale'],
                   marker_color='crimson', name='PML'),
            row=2, col=1
        )
        
        # Polices
        fig.add_trace(
            go.Bar(x=zones, y=analysis['by_zone']['Nb_Polices'],
                   marker_color='steelblue', name='Polices'),
            row=2, col=2
        )
        
        fig.update_layout(height=700, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        
        # Par type de risque
        st.subheader("Exposition par Type de Risque")
        fig_type = px.bar(
            analysis['by_type'],
            x='Type', y='Capital',
            color='Type',
            title='Capital par Type de Risque',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        st.plotly_chart(fig_type, use_container_width=True)
    
    with tab2:
        st.subheader("🗺️ Concentration Géographique des Risques")
        
        # Préparation des données pour la carte
        wilaya_data = analysis['by_wilaya'].copy()
        
        fig_map = px.scatter(
            wilaya_data,
            x='Wilaya',
            y='Capital_Total',
            color='Zone',
            size='PML',
            hover_data=['Nb_Polices', 'Pct_Portefeuille'],
            color_discrete_map={z: RPA99_ZONING[z]['color'] for z in RPA99_ZONING},
            title="Concentration du Capital par Wilaya",
            labels={'Capital_Total': 'Capital Assuré (DA)', 'Wilaya': 'Wilaya'}
        )
        
        fig_map.update_layout(xaxis_tickangle=-45, height=600)
        st.plotly_chart(fig_map, use_container_width=True)
    
    with tab3:
        st.subheader("🔴 Points Chauds (Hotspots)")
        st.markdown("Zones où le capital assuré dépasse 5% du portefeuille total")
        
        hotspots = analysis['by_wilaya'][analysis['by_wilaya']['HOTSPOT'] == True]
        
        if not hotspots.empty:
            st.dataframe(
                hotspots.sort_values('Capital_Total', ascending=False),
                use_container_width=True
            )
            
            # Alertes
            st.warning(f"⚠️ {len(hotspots)} wilayas en surconcentration détectées!")
        else:
            st.success("✅ Aucune surconcentration majeure détectée")
    
    with tab4:
        st.subheader("💡 Recommandations Stratégiques")
        
        # Surconcentrations
        if recommendations['surconcentration']:
            st.error("🚨 Zones de Surconcentration - Actions Requises:")
            for rec in recommendations['surconcentration'][:10]:
                st.markdown(f"""
                **{rec['wilaya']}** ({rec['zone']})
                - Capital: {rec['capital']:,.0f} DA ({rec['pct']:.2f}%)
                - PML: {rec['pml']:,.0f} DA
                - **Action:** {rec['action']}
                """)
        
        # Opportunités
        if recommendations['opportunities']:
            st.success("🟢 Opportunités de Développement:")
            for rec in recommendations['opportunities'][:5]:
                st.markdown(f"""
                **{rec['wilaya']}** ({rec['zone']})
                - Capital actuel: {rec['capital']:,.0f} DA
                - Potentiel: Développer le portefeuille
                """)
        
        # Alertes
        if recommendations['alerts']:
            st.warning("⚠️ Alertes:")
            for alert in recommendations['alerts']:
                st.markdown(f"- {alert}")
    
    with tab5:
        st.subheader("📋 Données Détaillées par Wilaya")
        
        st.dataframe(
            analysis['by_wilaya'].sort_values('Capital_Total', ascending=False),
            use_container_width=True
        )
        
        # Export
        csv = analysis['df'].to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Télécharger les Données Analysées (CSV)",
            data=csv,
            file_name='analyse_risque_sismique_complet.csv',
            mime='text/csv'
        )
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray;'>
        <p>Système d'Analyse du Risque Sismique - Conformément au RPA99/Version 2003</p>
        <p>Développé pour le Hackathon CATNAT 2026</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
    uploaded_file = st.file_uploader("CATNAT_2023_2025", type=['xlsx'])
    df = load_data(uploaded_file)