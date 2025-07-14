import dash
from dash import dcc, html, Input, Output
from dash import ctx
from shapely.geometry import Polygon, MultiPolygon
import plotly.graph_objects as go
import plotly.express as px
import geopandas as gpd
import pandas as pd

# -----------------------------
# Load and prep data
# -----------------------------

world = gpd.read_file("C:/Users/16122/Documents/MapSite/llama-homen/110m_cultural/ne_110m_admin_0_countries.shp")
world['geometry'] = world['geometry'].buffer(0)
world['ADM0_A3'] = world['ADM0_A3'].fillna('UNK')
world['POP_EST'] = world['POP_EST'].fillna(0)

#print(world.columns)
# -----------------------------
# Make Mapbox figure
# -----------------------------

# 1️⃣ Add population shading using choropleth_mapbox
choropleth = px.choropleth_map(
    world,
    geojson=world.__geo_interface__,
    locations=world['ADM0_A3'],
    featureidkey="properties.ADM0_A3",
    color="GDP_MD",
    color_continuous_scale="Viridis",
    opacity=0.25,  # <- controls transparency!
    hover_name="NAME",
    hover_data={"POP_EST": True, "ADM0_A3": True},
    custom_data=["POP_EST"],
    map_style="carto-positron",
    center={"lat": 20, "lon": 0},
    zoom=1,
)

choropleth.update_traces(
    hovertemplate="<b>%{location}</b><br>Population: %{customdata[0]:,}<extra></extra>"
)
fig = go.Figure(choropleth.data)  # Start with the fill layer

# 2️⃣ Add country borders as lines on top
for idx, row in world.iterrows():
    geom = row['geometry']
    if isinstance(geom, Polygon):
        polys = [geom]
    elif isinstance(geom, MultiPolygon):
        polys = geom.geoms
    else:
        polys = []

    for poly in polys:
        x, y = poly.exterior.coords.xy
        lon = list(x)
        lat = list(y)

        fig.add_trace(
            go.Scattermap(
                lon=lon,
                lat=lat,
                mode="lines",
                line=dict(width=1, color="black"),
                hoverinfo="skip",
                showlegend=False
            )
        )

# 3️⃣ Add pins on top
fig.add_trace(
    go.Scattermap(
        lon=[-74.006, 2.3522, 139.6917],
        lat=[40.7128, 48.8566, 35.6895],
        mode="markers",
        marker=dict(size=10, color="blue", symbol="marker"),
        text=["New York City", "Paris", "Tokyo"],
        hoverinfo="text",
        name="Pins"
    )
)

# 4️⃣ Final map layout tweaks
fig.update_layout(
    mapbox=dict(
        style="carto-positron",
        center={"lat": 20, "lon": 0},
        zoom=1,
    ),
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    showlegend=False
)

# -----------------------------
# Dash app
# -----------------------------

app = dash.Dash(__name__)

app.layout = html.Div([
    dcc.Graph(id="map", figure=fig, style={"height": "90vh"}),
    html.Div(id="country-info", style={"marginTop": 20, "fontSize": 18}),
    html.Button("Clear Selection", id="clear-btn", style={"marginTop": 10}),
    html.Div(id="gdp-graph", style={"marginTop": 40}),
    dcc.Store(id="selected-countries", data=[])
])

@app.callback(
    Output("selected-countries", "data"),
    Input("map", "clickData"),
    Input("clear-btn", "n_clicks"),
    Input("selected-countries", "data"),
    prevent_initial_call=True
)
def update_selection(clickData, clear_clicks, selected):
    triggered = ctx.triggered_id

    if triggered == "clear-btn":
        return []

    if triggered == "map" and clickData:
        point = clickData['points'][0]
        iso = point.get('location') or point.get('hovertext') or ''
        iso = iso.strip()

        if len(iso) != 3:
            return selected

        if iso in selected:
            selected.remove(iso)
        else:
            selected.append(iso)

        return selected

    return selected

@app.callback(
    Output("country-info", "children"),
    Output("gdp-graph", "children"),
    Input("selected-countries", "data")
)
def update_chart(selected):
    if not selected:
        return "Click countries to add them to a GDP bar chart.", html.Div()

    rows = world[world['ADM0_A3'].isin(selected)]
    df = rows[['NAME', 'GDP_MD']].copy()
    df = df.rename(columns={'NAME': 'Country'})

    fig = px.bar(
        df,
        x="Country",
        y="GDP_MD",
        title=f"GDP for selected countries",
        text_auto=True
    )

    return f"Selected countries: {', '.join(selected)}", dcc.Graph(figure=fig)

if __name__ == '__main__':
    app.run(debug=True)

server = app.server