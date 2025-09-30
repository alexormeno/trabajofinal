import os
import dash_bootstrap_components as dbc
from flask import Flask
from flask import Flask, request, make_response
import dash
from dash import html, dcc, Input, Output, State, ctx
from agent_ia import answer_rag_chain
import uuid

import re
from aget_bg import load_history_chat



def render_message(text, style):
    # Dividir el texto por bloques de iframe
    parts = re.split(r'(<iframe.*?</iframe>)', text, flags=re.DOTALL)

    children = []

    for part in parts:
        if "<iframe" in part:
            # Extraer el src del iframe
            match = re.search(r'src="([^"]+)"', part)
            if match:
                url = match.group(1)
                children.append(
                    html.Iframe(
                        src=url,
                        #width="560",
                        width="60%",
                        height="315",
                        style={
                            "border": "none",
                            "marginTop": "10px",
                            "borderRadius": "15px"  # bordes redondeados
                        }
                    )

                )
        else:
            # Si hay texto, lo mostramos como Markdown
            if part.strip():
                children.append(
                    dcc.Markdown(part, style={'whiteSpace': 'pre-wrap'})
                )

    return dbc.Card(html.Div(children), style=style, body=True)

    

server = Flask(__name__)

app = dash.Dash(server=server, 
                external_stylesheets=[dbc.themes.BOOTSTRAP])

#app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

@server.after_request
def add_client_id_cookie(response):
    """
    Verifica si el cliente ya tiene una cookie de identificación.
    Si no la tiene, genera un nuevo UUID y la establece.
    """
    client_id = request.cookies.get('client_id')
    if client_id is None:
        new_uuid = str(uuid.uuid4())
        response.set_cookie('client_id', new_uuid, max_age=365*24*60*60)  # Cookie válida por 1 año
    return response


app.layout = dbc.Container([
    # NAVBAR
    dbc.Navbar(
        dbc.Container([
            dbc.Row([
                dbc.Col(
                    html.H2(
                        "Asistente Virtual Informática II",
                        className="text-center mb-0",
                        style={"fontWeight": "600", "color": "#333"}
                    ),
                    xs=12, sm=12, md=12, lg=12, xl=12  # ocupa todo el ancho en cualquier dispositivo
                )
            ], justify="center", className="w-100")
        ]),
        color="#e9ecef",
        dark=False,
        className="mb-4 shadow-sm",
        style={"padding": "10px"}
    ),

    # CONTENEDOR PRINCIPAL
    html.Div([
        # CHAT CONTAINER
        html.Div(id='chat-container', children=[], style={
            'border': '1px solid #dee2e6',
            'padding': '20px',
            'height': '60vh',
            'overflowY': 'auto',
            'backgroundColor': '#ffffff',
            'borderRadius': '10px',
            'boxShadow': '0 2px 8px rgba(0, 0, 0, 0.05)',
        }),

        # INPUT Y BOTÓN
        dcc.Loading(
            dbc.Row([
                dbc.Col([
                    dcc.Input(
                        id='user-input',
                        type='text',
                        placeholder='Escribe tu mensaje...',
                        className='form-control',
                        debounce=True,
                        n_submit=0,
                        style={'width': '100%'}  # asegura que se adapte al contenedor
                    )
                ], xs=9, sm=10, md=10, lg=10, xl=10),

                dbc.Col([
                    dbc.Button('Enviar', id='send-button', color='primary', className='w-100')
                ], xs=3, sm=2, md=2, lg=2, xl=2),
            ], className='mt-3 g-2'),  # g-2 agrega espacio entre columnas
        ),

        dcc.Store(id='chat-history', data=[]),
        dcc.Store(id='scroll-dummy', data=[])

    ], style={
        'maxWidth': '100%',
        'margin': '0 auto',
        'padding': '20px',
        'backgroundColor': '#f8f9fa',
        'borderRadius': '12px',
        'boxShadow': '0 6px 16px rgba(0, 0, 0, 0.06)'
    })
], fluid=True)

@app.callback(
    Output('chat-history', 'data'),
    Output('user-input', 'value'),
    Input('send-button', 'n_clicks'),
    Input('user-input', 'n_submit'),
    State('user-input', 'value'),
    State('chat-history', 'data'),
    #prevent_initial_call=True
)
def update_chat(n_clicks, n_submit, user_input, chat_history_f):
    if not user_input:
        client_id = request.cookies.get('client_id')
        historial = load_history_chat('f314873f-9c40-4c41-9368-4eb2bb234f6e')

        return historial, ""#dash.exceptions.PreventUpdate

    #respuesta = f"Esta es una respuesta generada para: {user_input}"
    #respuesta = interactuar(user_input)
    #respuesta = respuesta['message']
        
    # Detectar qué disparó el callback
    trigger = ctx.triggered_id

    if trigger in ['send-button', 'user-input']:

        #thread_id = uuid.uuid4()
        client_id = request.cookies.get('client_id')
        
        #save_message(client_id, 'human', user_input)
        respuesta = answer_rag_chain(user_input, client_id) # acá iría tu LLM o lógica de respuesta
        #save_message(client_id, 'ai', respuesta)

        
        chat_history_f.append({'role': 'human', 'message': user_input})
        chat_history_f.append({'role': 'ai', 'message': respuesta})
        return chat_history_f, ""


    return chat_history_f, ""


# --- Callback para renderizar el historial de chat (incluye la lógica de render_textbox) ---
@app.callback(
    Output('chat-container', 'children'),
    Input('chat-history', 'data')
)
def render_chat(chat_history):
    messages = []
    
    # Rutas a las imágenes en la carpeta 'assets'
    img_ai_path = app.get_asset_url("astronaut_212101.png")
    img_human_path = app.get_asset_url("school_10945142.png")
    
    for item in chat_history:
        text = item['message']
        role = item['role']
        
        # Estilo base
        style = {
            "maxWidth": "70%",
            "padding": "10px 15px",
            "borderRadius": "10px",
            "marginBottom": "10px",
            "boxShadow": "0 2px 6px rgba(0,0,0,0.05)",
        }
        
        if role == 'human':
            # Estilos y alineación para el usuario
            style["marginLeft"] = "auto"
            style["backgroundColor"] = "#cce5ff"
            style["color"] = "#004085"
            card = dbc.Card(dcc.Markdown(text, style={'whiteSpace': 'pre-wrap'}), style=style, body=True)
            avatar = html.Img(src=img_human_path, style={"height": "40px", "borderRadius": "50%", "marginLeft": "10px"})
            messages.append(html.Div([card, avatar], style={'display': 'flex', 'alignItems': 'start', 'justifyContent': 'flex-end'}))
        
        elif role == 'ai':
            # Estilos y alineación para la IA
            style["marginLeft"] = 0
            style["backgroundColor"] = "#e2e3e5"
            style["color"] = "#212529"
            #card = dbc.Card(dcc.Markdown(text, style={'whiteSpace': 'pre-wrap'}), style=style, body=True)
            card = render_message(text, style)
            avatar = html.Img(src=img_ai_path, style={"height": "40px", "borderRadius": "50%", "marginRight": "10px"})
            messages.append(html.Div([avatar, card], style={'display': 'flex', 'alignItems': 'start', 'justifyContent': 'flex-start'}))
        
    return messages

# ⚡ Auto-scroll con JS en cliente
app.clientside_callback(
    """
    function(children) {
        var chatBox = document.getElementById("chat-container");
        if (chatBox){
            chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: 'smooth' });
        }
        return "";
    }
    """,
    Output("scroll-dummy", "data"),   # usamos un store dummy
    Input("chat-container", "children")
)



if __name__ == '__main__':
    app.run(host="0.0.0.0",
            port=8081)