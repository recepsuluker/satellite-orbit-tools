import plotly.graph_objects as go
from skyfield.api import load

from .utils import get_active_satellites, get_ground_station


def generate_sky_view(output_path="static/satellite_sky_view.html"):
    try:
        satellites, _ = get_active_satellites()
        station, _ = get_ground_station()
        if not satellites:
            return False

        ts = load.timescale()
        now = ts.now()

        fig = go.Figure()
        colors = ["#00f2ff", "#ff00ea", "#00ff88", "#ffea00", "#ff4d4d"]

        for i, sat in enumerate(satellites):
            diff = (sat - station).at(now)
            alt, az, distance = diff.altaz()

            # Sadece ufkumuzun üzerindekileri net gösterelim
            is_visible = alt.degrees > 0

            fig.add_trace(
                go.Scatterpolar(
                    r=[90 - alt.degrees],  # Merkez 90 derece (tam tepemiz), kenarlar 0 derece (ufuk)
                    theta=[az.degrees],
                    mode="markers+text",
                    marker=dict(
                        size=12 if is_visible else 8,
                        color=colors[i % len(colors)],
                        line=dict(color="white", width=2 if is_visible else 0),
                        opacity=1.0 if is_visible else 0.3,
                    ),
                    text=[sat.name if is_visible else ""],
                    textposition="top center",
                    name=sat.name,
                )
            )

        fig.update_layout(
            template="plotly_dark",
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(visible=True, range=[0, 90], showticklabels=False, ticks=""),
                angularaxis=dict(rotation=90, direction="clockwise"),
            ),
            showlegend=False,
            margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )

        fig.write_html(output_path, full_html=True, include_plotlyjs="cdn")
        return True
    except Exception as e:
        print(f"❌ Sky View hatası: {e}")
        return False


if __name__ == "__main__":
    generate_sky_view()
