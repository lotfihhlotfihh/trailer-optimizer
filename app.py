import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from optimizer import Item, TrailerOptimizer, COLORS

TRAILER_PRESETS = {
    "Semi-remorque EU standard (13.6m)": (13.6, 2.4, 2.7, 24000),
    "Remorque courte (8m)": (8.0, 2.4, 2.7, 15000),
    "Camion porteur (7m)": (7.0, 2.4, 2.4, 12000),
    "Fourgon (4.5m)": (4.5, 2.0, 2.1, 3500),
    "Personnalisé": None,
}

EXAMPLE_LOTS = {
    "CMD-001": {
        "palettes": [
            {"nom": "Palette EUR", "L": 1.2, "l": 0.8, "H": 1.2, "poids": 400, "fragile": False, "non_gerbable": False, "qty": 4},
            {"nom": "Gros colis", "L": 2.0, "l": 1.0, "H": 1.5, "poids": 800, "fragile": False, "non_gerbable": False, "qty": 1},
        ]
    },
    "CMD-002": {
        "palettes": [
            {"nom": "Palette lourde", "L": 1.2, "l": 0.8, "H": 1.4, "poids": 1200, "fragile": False, "non_gerbable": True, "qty": 2},
            {"nom": "Caisse fragile", "L": 0.6, "l": 0.4, "H": 0.5, "poids": 30, "fragile": True, "non_gerbable": False, "qty": 3},
        ]
    },
    "CMD-003": {
        "palettes": [
            {"nom": "Colis divers", "L": 0.8, "l": 0.6, "H": 0.6, "poids": 150, "fragile": False, "non_gerbable": False, "qty": 3},
            {"nom": "Colis non gerbable", "L": 0.8, "l": 0.6, "H": 0.8, "poids": 120, "fragile": False, "non_gerbable": True, "qty": 2},
        ]
    },
}


def get_lot_color(lot_name, lots_list):
    if lot_name in lots_list:
        idx = lots_list.index(lot_name)
    else:
        idx = 0
    return COLORS[idx % len(COLORS)]


def make_box_mesh(x, y, z, dx, dy, dz, color, name, lot_name, opacity=0.75):
    vx = [x, x+dx, x+dx, x,    x,    x+dx, x+dx, x]
    vy = [y, y,    y+dy, y+dy, y,    y,    y+dy, y+dy]
    vz = [z, z,    z,    z,    z+dz, z+dz, z+dz, z+dz]
    i_ = [0, 0, 4, 4, 0, 0, 2, 2, 0, 0, 1, 1]
    j_ = [1, 2, 5, 6, 1, 5, 3, 7, 3, 7, 2, 6]
    k_ = [2, 3, 6, 7, 5, 4, 7, 6, 7, 4, 6, 5]
    return go.Mesh3d(
        x=vx, y=vy, z=vz,
        i=i_, j=j_, k=k_,
        color=color, opacity=opacity,
        name=name, showscale=False,
        legendgroup=lot_name,
        legendgrouptitle_text=lot_name,
        hovertemplate=(
            f"<b>{name}</b><br>"
            f"Lot: {lot_name}<br>"
            f"Pos: ({x:.2f}, {y:.2f}, {z:.2f}) m<br>"
            f"Dim: {dx:.2f}x{dy:.2f}x{dz:.2f} m<extra></extra>"
        )
    )


def make_trailer_wireframe(tl, tw, th):
    pts = [
        (0,0,0),(tl,0,0),(tl,tw,0),(0,tw,0),(0,0,0), None,
        (0,0,th),(tl,0,th),(tl,tw,th),(0,tw,th),(0,0,th), None,
        (0,0,0),(0,0,th), None,
        (tl,0,0),(tl,0,th), None,
        (tl,tw,0),(tl,tw,th), None,
        (0,tw,0),(0,tw,th), None,
    ]
    xs = [p[0] if p else None for p in pts]
    ys = [p[1] if p else None for p in pts]
    zs = [p[2] if p else None for p in pts]
    return go.Scatter3d(
        x=xs, y=ys, z=zs, mode='lines',
        line=dict(color='rgba(50,50,50,0.4)', width=3),
        name='Remorque', showlegend=True,
        hoverinfo='skip'
    )


def build_figure(placements, tl, tw, th):
    fig = go.Figure()
    fig.add_trace(make_trailer_wireframe(tl, tw, th))

    for p in placements:
        fig.add_trace(make_box_mesh(
            p.x, p.y, p.z, p.l, p.w, p.h,
            p.item.color, p.item.name, p.item.lot
        ))
        fig.add_trace(go.Scatter3d(
            x=[p.x + p.l/2], y=[p.y + p.w/2], z=[p.z + p.h/2],
            mode='text', text=[p.item.name[:12]],
            textfont=dict(size=8, color='#111'),
            showlegend=False, hoverinfo='skip',
            legendgroup=p.item.lot,
        ))

    scale = 5.0 / tl
    fig.update_layout(
        scene=dict(
            xaxis_title='Longueur (m)',
            yaxis_title='Largeur (m)',
            zaxis_title='Hauteur (m)',
            xaxis=dict(range=[0, tl]),
            yaxis=dict(range=[0, tw]),
            zaxis=dict(range=[0, th]),
            aspectmode='manual',
            aspectratio=dict(x=5, y=max(tw * scale * 2, 0.6), z=max(th * scale * 2, 0.6)),
        ),
        height=580,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation='v', x=1.02, font=dict(size=11), groupclick='toggleitem'),
    )
    return fig


# ─── Streamlit App ───────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="Optimiseur de Chargement",
        page_icon="🚛",
        layout="wide"
    )

    st.title("🚛 Optimiseur de Chargement de Remorque")
    st.caption("Algorithme 3D bin-packing avec contraintes de poids, fragilite et support")

    # Session state
    if 'lots' not in st.session_state:
        st.session_state.lots = {}  # {lot_name: [Item, ...]}
    if 'counter' not in st.session_state:
        st.session_state.counter = 0
    if 'result' not in st.session_state:
        st.session_state.result = None

    def get_all_items():
        all_items = []
        for items in st.session_state.lots.values():
            all_items.extend(items)
        return all_items

    def lot_names():
        return list(st.session_state.lots.keys())

    # ── Sidebar: trailer config ───────────────────────────────────────────────
    with st.sidebar:
        st.header("Configuration Remorque")
        preset = st.selectbox("Type de remorque", list(TRAILER_PRESETS.keys()))

        if TRAILER_PRESETS[preset] is not None:
            tl, tw, th, mw = TRAILER_PRESETS[preset]
            st.info(f"L: **{tl}m** | l: **{tw}m** | H: **{th}m** | Max: **{mw:,} kg**")
        else:
            tl = st.number_input("Longueur (m)", 1.0, 25.0, 13.6, 0.1)
            tw = st.number_input("Largeur (m)", 0.5, 5.0, 2.4, 0.1)
            th = st.number_input("Hauteur (m)", 0.5, 5.0, 2.7, 0.1)
            mw = st.number_input("Poids max (kg)", 100, 100000, 24000, 100)

        st.divider()
        st.metric("Volume remorque", f"{tl*tw*th:.1f} m3")
        st.metric("Charge maximale", f"{mw:,} kg")

        all_items = get_all_items()
        if all_items:
            total_w = sum(i.weight for i in all_items)
            total_v = sum(i.volume for i in all_items)
            st.divider()
            st.metric("Lots", len(st.session_state.lots))
            st.metric("Palettes total", len(all_items))
            st.metric("Poids total", f"{total_w:,.0f} kg")
            st.metric("Volume total", f"{total_v:.2f} m3")

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["📦 Commandes / Lots", "🗺️ Resultat 3D", "📂 Import Longitude"])

    # ── Tab 1: Lots & palettes ───────────────────────────────────────────────
    with tab1:
        col_form, col_list = st.columns([1, 2])

        with col_form:
            st.subheader("Ajouter un lot / commande")
            with st.form("add_lot_form", clear_on_submit=True):
                lot_name = st.text_input("Nom du lot / commande", placeholder="Ex: CMD-001, LOT-A")
                st.markdown("---")
                st.markdown("**Palette / colis dans ce lot :**")
                item_name = st.text_input("Nom palette", placeholder="Ex: Palette EUR, Colis fragile")
                c1, c2, c3 = st.columns(3)
                length = c1.number_input("L (m)", 0.1, 15.0, 1.2, 0.05)
                width  = c2.number_input("l (m)", 0.1,  3.0, 0.8, 0.05)
                height = c3.number_input("H (m)", 0.1,  3.0, 1.0, 0.05)
                weight = st.number_input("Poids (kg)", 0.1, 20000.0, 400.0, 10.0)
                c4, c5, c6 = st.columns(3)
                fragile      = c4.checkbox("Fragile")
                non_gerbable = c5.checkbox("Non gerbable")
                can_rotate   = c6.checkbox("Rotation OK", value=True)
                qty = st.number_input("Quantite", 1, 100, 1)
                ok = st.form_submit_button("Ajouter au lot", use_container_width=True, type="primary")

                if ok and lot_name.strip() and item_name.strip():
                    ln = lot_name.strip()
                    if ln not in st.session_state.lots:
                        st.session_state.lots[ln] = []
                    color = get_lot_color(ln, lot_names())
                    for i in range(int(qty)):
                        st.session_state.counter += 1
                        label = item_name.strip() if qty == 1 else f"{item_name.strip()} #{i+1}"
                        st.session_state.lots[ln].append(Item(
                            st.session_state.counter, label,
                            length, width, height, weight,
                            fragile, can_rotate, non_gerbable, ln, color
                        ))
                    st.session_state.result = None
                    st.success(f"{int(qty)}x '{item_name.strip()}' ajoute au lot **{ln}**")

        with col_list:
            n_lots = len(st.session_state.lots)
            n_items = len(get_all_items())
            st.subheader(f"Commandes — {n_lots} lot(s), {n_items} palette(s)")

            if n_lots:
                for lot_name, items in st.session_state.lots.items():
                    color = get_lot_color(lot_name, lot_names())
                    total_w = sum(i.weight for i in items)
                    total_v = sum(i.volume for i in items)
                    header = f"🟦 **{lot_name}** — {len(items)} palette(s) | {total_w:,.0f} kg | {total_v:.2f} m3"

                    with st.expander(header):
                        rows = []
                        for it in items:
                            rows.append({
                                'Nom': it.name,
                                'L': it.length, 'l': it.width, 'H': it.height,
                                'Poids (kg)': it.weight,
                                'Vol (m3)': round(it.volume, 3),
                                'Fragile': 'OUI' if it.fragile else '',
                                'Non gerbable': 'OUI' if it.non_gerbable else '',
                            })
                        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

                        if st.button(f"Supprimer {lot_name}", key=f"del_{lot_name}"):
                            del st.session_state.lots[lot_name]
                            st.session_state.result = None
                            st.rerun()

                st.markdown("---")
                bc1, bc2 = st.columns(2)
                if bc1.button("Vider tout", use_container_width=True):
                    st.session_state.lots = {}
                    st.session_state.result = None
                    st.rerun()

                if bc2.button("Optimiser le chargement", use_container_width=True, type="primary"):
                    all_items = get_all_items()
                    with st.spinner("Calcul en cours..."):
                        opt = TrailerOptimizer(tl, tw, th, mw)
                        placements, unplaced = opt.optimize(all_items)
                        st.session_state.result = {
                            'placements': placements,
                            'unplaced': unplaced,
                            'stats': opt.get_stats(),
                            'tl': tl, 'tw': tw, 'th': th,
                        }
                    st.success("Optimisation terminee ! Voir l'onglet Resultat 3D.")
            else:
                st.info("Ajoutez des lots / commandes pour commencer.")
                if st.button("Charger des exemples"):
                    st.session_state.lots = {}
                    for lot_name, lot_data in EXAMPLE_LOTS.items():
                        st.session_state.lots[lot_name] = []
                        color = get_lot_color(lot_name, list(EXAMPLE_LOTS.keys()))
                        for p in lot_data["palettes"]:
                            for i in range(p["qty"]):
                                st.session_state.counter += 1
                                label = p["nom"] if p["qty"] == 1 else f"{p['nom']} #{i+1}"
                                st.session_state.lots[lot_name].append(Item(
                                    st.session_state.counter, label,
                                    p["L"], p["l"], p["H"], p["poids"],
                                    p["fragile"], True, p["non_gerbable"],
                                    lot_name, color
                                ))
                    st.rerun()

    # ── Tab 2: Results ────────────────────────────────────────────────────────
    with tab2:
        if not st.session_state.result:
            st.info("Ajoutez des commandes et lancez l'optimisation.")
        else:
            res = st.session_state.result
            stats = res['stats']
            placements = res['placements']
            unplaced = res['unplaced']

            # KPIs
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Taux de remplissage", f"{stats['fill_rate']:.1f}%")
            c2.metric("Poids charge", f"{stats['total_weight']:,.0f} kg",
                      f"{stats['weight_rate']:.1f}% du max")
            c3.metric("Articles places", stats['items_placed'])
            c4.metric("Non places", len(unplaced),
                      delta_color="inverse" if unplaced else "off")

            if unplaced:
                st.warning(f"Non place(s) : {', '.join(f'{i.name} ({i.lot})' for i in unplaced)}")

            # 3D chart
            st.plotly_chart(
                build_figure(placements, res['tl'], res['tw'], res['th']),
                use_container_width=True
            )
            st.caption("Cliquez sur un lot dans la legende pour l'afficher/masquer")

            # Plan par lot
            st.subheader("Plan de chargement par lot")
            lots_in_plan = {}
            for idx, p in enumerate(placements, 1):
                lot = p.item.lot
                if lot not in lots_in_plan:
                    lots_in_plan[lot] = []
                lots_in_plan[lot].append((idx, p))

            for lot_name, lot_placements in lots_in_plan.items():
                color = lot_placements[0][1].item.color
                with st.expander(f"**{lot_name}** — {len(lot_placements)} palette(s) placee(s)"):
                    plan = []
                    for idx, p in lot_placements:
                        plan.append({
                            'Ordre': idx,
                            'Article': p.item.name,
                            'X (m)': round(p.x, 2),
                            'Y (m)': round(p.y, 2),
                            'Z (m)': round(p.z, 2),
                            'L (m)': round(p.l, 2),
                            'l (m)': round(p.w, 2),
                            'H (m)': round(p.h, 2),
                            'Poids (kg)': p.item.weight,
                            'Fragile': 'OUI' if p.item.fragile else '',
                            'Non gerbable': 'OUI' if p.item.non_gerbable else '',
                        })
                    st.dataframe(pd.DataFrame(plan), hide_index=True, use_container_width=True)

            # Export CSV global
            all_plan = []
            for idx, p in enumerate(placements, 1):
                all_plan.append({
                    'Ordre': idx, 'Lot': p.item.lot, 'Article': p.item.name,
                    'X (m)': round(p.x, 2), 'Y (m)': round(p.y, 2), 'Z (m)': round(p.z, 2),
                    'L (m)': round(p.l, 2), 'l (m)': round(p.w, 2), 'H (m)': round(p.h, 2),
                    'Poids (kg)': p.item.weight,
                    'Fragile': 'OUI' if p.item.fragile else '',
                    'Non gerbable': 'OUI' if p.item.non_gerbable else '',
                })
            df_plan = pd.DataFrame(all_plan)
            csv = df_plan.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Telecharger le plan complet (CSV)",
                csv, "plan_chargement.csv", "text/csv"
            )

    # ── Tab 3: Import Longitude ────────────────────────────────────────────
    with tab3:
        st.subheader("Importer depuis Longitude")
        st.markdown("""
        Exportez vos marchandises depuis **Longitude** en format **CSV** ou **Excel (.xlsx)**.

        Le fichier doit contenir ces colonnes (les noms sont flexibles) :
        - **Lot** (ou Commande, Ordre, N commande) — pour regrouper les palettes
        - **Nom** (ou Reference, Designation, Article)
        - **Longueur** (en metres)
        - **Largeur** (en metres)
        - **Hauteur** (en metres)
        - **Poids** (en kg)
        - **Fragile** (optionnel : oui/non)
        - **Non gerbable** (optionnel : oui/non)
        - **Quantite** (optionnel, defaut = 1)
        """)

        uploaded = st.file_uploader("Choisir un fichier CSV ou Excel", type=["csv", "xlsx", "xls"])

        if uploaded:
            try:
                if uploaded.name.endswith('.csv'):
                    df = pd.read_csv(uploaded, sep=None, engine='python')
                else:
                    df = pd.read_excel(uploaded)

                st.dataframe(df, use_container_width=True)

                # Auto-detect columns
                col_map = {}
                for col in df.columns:
                    cl = col.strip().lower()
                    if cl in ('lot', 'commande', 'ordre', 'n commande', 'no commande', 'num commande', 'command', 'order', 'cmd'):
                        col_map['lot'] = col
                    elif cl in ('nom', 'name', 'reference', 'designation', 'article', 'libelle'):
                        col_map['nom'] = col
                    elif cl in ('longueur', 'length', 'long', 'l'):
                        col_map['longueur'] = col
                    elif cl in ('largeur', 'width', 'larg', 'w'):
                        col_map['largeur'] = col
                    elif cl in ('hauteur', 'height', 'haut', 'h'):
                        col_map['hauteur'] = col
                    elif cl in ('poids', 'weight', 'masse', 'kg'):
                        col_map['poids'] = col
                    elif cl in ('fragile',):
                        col_map['fragile'] = col
                    elif cl in ('non gerbable', 'nongerbable', 'non_gerbable', 'stackable', 'gerbable'):
                        col_map['non_gerbable'] = col
                    elif cl in ('quantite', 'qty', 'quantity'):
                        col_map['qty'] = col

                required = ['nom', 'longueur', 'largeur', 'hauteur', 'poids']
                missing = [r for r in required if r not in col_map]

                if missing:
                    st.error(f"Colonnes manquantes : {', '.join(missing)}")
                    st.info(f"Colonnes detectees : {list(df.columns)}")
                else:
                    st.success(f"Colonnes detectees : {col_map}")

                    if st.button("Importer les marchandises", type="primary"):
                        count = 0
                        imported_lots = {}

                        for _, row in df.iterrows():
                            # Lot name
                            if 'lot' in col_map:
                                ln = str(row[col_map['lot']]).strip()
                            else:
                                ln = "Import Longitude"

                            nom = str(row[col_map['nom']])
                            longueur = float(row[col_map['longueur']])
                            largeur = float(row[col_map['largeur']])
                            hauteur = float(row[col_map['hauteur']])
                            poids = float(row[col_map['poids']])

                            fragile = False
                            if 'fragile' in col_map:
                                v = str(row[col_map['fragile']]).strip().lower()
                                fragile = v in ('oui', 'yes', '1', 'true', 'vrai', 'x')

                            non_gerb = False
                            if 'non_gerbable' in col_map:
                                v = str(row[col_map['non_gerbable']]).strip().lower()
                                non_gerb = v in ('oui', 'yes', '1', 'true', 'vrai', 'x')

                            qty = 1
                            if 'qty' in col_map:
                                try:
                                    qty = int(row[col_map['qty']])
                                except (ValueError, TypeError):
                                    qty = 1

                            if ln not in st.session_state.lots:
                                st.session_state.lots[ln] = []
                            if ln not in imported_lots:
                                imported_lots[ln] = 0

                            all_lot_names = lot_names()
                            color = get_lot_color(ln, all_lot_names)

                            for i in range(qty):
                                st.session_state.counter += 1
                                label = nom if qty == 1 else f"{nom} #{i+1}"
                                st.session_state.lots[ln].append(Item(
                                    st.session_state.counter, label,
                                    longueur, largeur, hauteur, poids,
                                    fragile, True, non_gerb, ln, color
                                ))
                                count += 1
                                imported_lots[ln] += 1

                        st.session_state.result = None
                        summary = ", ".join(f"**{k}** ({v})" for k, v in imported_lots.items())
                        st.success(f"{count} palette(s) importee(s) dans {len(imported_lots)} lot(s) : {summary}")
                        st.rerun()

            except Exception as e:
                st.error(f"Erreur de lecture : {e}")


if __name__ == "__main__":
    main()
