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

EXAMPLE_ITEMS = [
    (1, "Palette EUR #1", 1.2, 0.8, 1.2, 400, False, True, COLORS[0]),
    (2, "Palette EUR #2", 1.2, 0.8, 1.2, 380, False, True, COLORS[1]),
    (3, "Palette EUR #3", 1.2, 0.8, 1.0, 350, False, True, COLORS[2]),
    (4, "Palette EUR #4", 1.2, 0.8, 1.0, 300, False, True, COLORS[3]),
    (5, "Gros colis", 2.0, 1.0, 1.5, 800, False, True, COLORS[4]),
    (6, "Palette lourde", 1.2, 0.8, 1.4, 1200, False, False, COLORS[5]),
    (7, "Caisse fragile A", 0.6, 0.4, 0.5, 30, True, False, COLORS[6]),
    (8, "Caisse fragile B", 0.8, 0.6, 0.4, 20, True, False, COLORS[7]),
    (9, "Colis divers #1", 0.8, 0.6, 0.6, 150, False, True, COLORS[8]),
    (10, "Colis divers #2", 0.6, 0.6, 0.8, 120, False, True, COLORS[9]),
]


def make_box_mesh(x, y, z, dx, dy, dz, color, name, opacity=0.75):
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
        hovertemplate=(
            f"<b>{name}</b><br>"
            f"Pos: ({x:.2f}, {y:.2f}, {z:.2f}) m<br>"
            f"Dim: {dx:.2f}×{dy:.2f}×{dz:.2f} m<extra></extra>"
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
            p.item.color, p.item.name
        ))
        fig.add_trace(go.Scatter3d(
            x=[p.x + p.l/2], y=[p.y + p.w/2], z=[p.z + p.h/2],
            mode='text', text=[p.item.name[:12]],
            textfont=dict(size=8, color='#111'),
            showlegend=False, hoverinfo='skip'
        ))

    scale = 5.0 / tl
    fig.update_layout(
        scene=dict(
            xaxis_title='Longueur →  (m)',
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
        legend=dict(orientation='v', x=1.02, font=dict(size=11)),
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
    st.caption("Algorithme 3D bin-packing avec contraintes de poids, fragilité et support")

    # Session state
    if 'cargo' not in st.session_state:
        st.session_state.cargo = []
    if 'counter' not in st.session_state:
        st.session_state.counter = 0
    if 'result' not in st.session_state:
        st.session_state.result = None

    # ── Sidebar: trailer config ───────────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Configuration Remorque")
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
        st.metric("Volume remorque", f"{tl*tw*th:.1f} m³")
        st.metric("Charge maximale", f"{mw:,} kg")

        if st.session_state.cargo:
            total_w = sum(i.weight for i in st.session_state.cargo)
            total_v = sum(i.volume for i in st.session_state.cargo)
            st.divider()
            st.metric("Poids liste", f"{total_w:,.0f} kg")
            st.metric("Volume liste", f"{total_v:.2f} m³")

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab1, tab2 = st.tabs(["📦 Marchandises", "🗺️ Résultat 3D"])

    # ── Tab 1: Add items ──────────────────────────────────────────────────────
    with tab1:
        col_form, col_list = st.columns([1, 2])

        with col_form:
            st.subheader("Ajouter une marchandise")
            with st.form("add_form", clear_on_submit=True):
                name = st.text_input("Nom / référence", placeholder="Ex: Palette EUR, Colis #1")
                c1, c2, c3 = st.columns(3)
                length = c1.number_input("L (m)", 0.1, 15.0, 1.2, 0.05)
                width  = c2.number_input("l (m)", 0.1,  3.0, 0.8, 0.05)
                height = c3.number_input("H (m)", 0.1,  3.0, 1.0, 0.05)
                weight = st.number_input("Poids (kg)", 0.1, 20000.0, 400.0, 10.0)
                c4, c5 = st.columns(2)
                fragile    = c4.checkbox("🔴 Fragile")
                can_rotate = c5.checkbox("🔄 Rotation OK", value=True)
                qty = st.number_input("Quantité", 1, 50, 1)
                ok = st.form_submit_button("➕ Ajouter", use_container_width=True, type="primary")

                if ok and name.strip():
                    for i in range(int(qty)):
                        st.session_state.counter += 1
                        color = COLORS[st.session_state.counter % len(COLORS)]
                        label = name.strip() if qty == 1 else f"{name.strip()} #{i+1}"
                        st.session_state.cargo.append(Item(
                            st.session_state.counter, label,
                            length, width, height, weight,
                            fragile, can_rotate, color
                        ))
                    st.session_state.result = None
                    st.success(f"✅ {int(qty)}× '{name.strip()}' ajouté(s)")

        with col_list:
            n = len(st.session_state.cargo)
            st.subheader(f"Liste — {n} article(s)")

            if n:
                rows = []
                for it in st.session_state.cargo:
                    rows.append({
                        'ID': it.id, 'Nom': it.name,
                        'L': it.length, 'l': it.width, 'H': it.height,
                        'Poids (kg)': it.weight,
                        'Vol (m³)': round(it.volume, 3),
                        'Fragile': '🔴' if it.fragile else '',
                        'Rotation': '✅' if it.can_rotate else '❌',
                    })
                st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

                bc1, bc2 = st.columns(2)
                if bc1.button("🗑️ Vider la liste", use_container_width=True):
                    st.session_state.cargo = []
                    st.session_state.result = None
                    st.rerun()

                if bc2.button("🚀 Optimiser le chargement", use_container_width=True, type="primary"):
                    with st.spinner("Calcul en cours…"):
                        opt = TrailerOptimizer(tl, tw, th, mw)
                        placements, unplaced = opt.optimize(st.session_state.cargo)
                        st.session_state.result = {
                            'placements': placements,
                            'unplaced': unplaced,
                            'stats': opt.get_stats(),
                            'tl': tl, 'tw': tw, 'th': th,
                        }
                    st.success("✅ Optimisation terminée ! Voir l'onglet Résultat 3D.")
            else:
                st.info("Ajoutez des marchandises pour commencer.")
                if st.button("📦 Charger des exemples"):
                    st.session_state.cargo = [
                        Item(*row) for row in EXAMPLE_ITEMS
                    ]
                    st.session_state.counter = len(EXAMPLE_ITEMS)
                    st.rerun()

    # ── Tab 2: Results ────────────────────────────────────────────────────────
    with tab2:
        if not st.session_state.result:
            st.info("👈 Ajoutez des marchandises et lancez l'optimisation.")
        else:
            res = st.session_state.result
            stats = res['stats']
            placements = res['placements']
            unplaced = res['unplaced']

            # KPIs
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Taux de remplissage", f"{stats['fill_rate']:.1f}%")
            c2.metric("Poids chargé", f"{stats['total_weight']:,.0f} kg",
                      f"{stats['weight_rate']:.1f}% du max")
            c3.metric("Articles placés", stats['items_placed'])
            c4.metric("Non placés", len(unplaced),
                      delta_color="inverse" if unplaced else "off")

            if unplaced:
                st.warning(f"⚠️ Non placé(s) : {', '.join(i.name for i in unplaced)}")

            # 3D chart
            st.plotly_chart(
                build_figure(placements, res['tl'], res['tw'], res['th']),
                use_container_width=True
            )

            # Plan table
            st.subheader("📋 Plan de chargement")
            plan = []
            for idx, p in enumerate(placements, 1):
                plan.append({
                    'Ordre': idx,
                    'Article': p.item.name,
                    'X départ (m)': round(p.x, 2),
                    'Y départ (m)': round(p.y, 2),
                    'Z départ (m)': round(p.z, 2),
                    'L (m)': round(p.l, 2),
                    'l (m)': round(p.w, 2),
                    'H (m)': round(p.h, 2),
                    'Poids (kg)': p.item.weight,
                    'Fragile': '🔴' if p.item.fragile else '',
                })
            df_plan = pd.DataFrame(plan)
            st.dataframe(df_plan, hide_index=True, use_container_width=True)

            csv = df_plan.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Télécharger le plan (CSV)",
                csv, "plan_chargement.csv", "text/csv"
            )


if __name__ == "__main__":
    main()
