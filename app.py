import os
import dash_bootstrap_components as dbc
from flask import Flask
from flask import Flask, request, make_response
import dash
from dash import html, dcc, Input, Output, State, ctx
from agent_ia import answer_rag_chain
import uuid


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
    dbc.Navbar(
        dbc.Container([
            dbc.Row([
                dbc.Col(html.H2("Asistente Virtual Informática II", className="text-center w-100 mb-0", style={
                    "fontWeight": "600",
                    "color": "#333",
                }))
            ], justify="center", className="w-100")
        ]),
        color="#e9ecef",
        dark=False,
        className="mb-4 shadow-sm",
        style={"padding": "10px"}
    ),

    html.Div([
        html.Div(id='chat-container', children=[], style={
            'border': '1px solid #dee2e6',
            'padding': '20px',
            'height': '60vh',
            'overflowY': 'scroll',
            'backgroundColor': '#ffffff',
            'borderRadius': '10px',
            'boxShadow': '0 2px 8px rgba(0, 0, 0, 0.05)',
        }),
        dcc.Loading(
            dbc.Row([
                dbc.Col([
                    dcc.Input(
                        id='user-input',
                        type='text',
                        placeholder='Escribe tu mensaje...',
                        className='form-control',
                        debounce=True,
                        n_submit=0
                    )
                ], width=10),
                dbc.Col([
                    dbc.Button('Enviar', id='send-button', color='primary', className='w-100')
                ], width=2),
            ], className='mt-3'),
            
        ),


        dcc.Store(id='chat-history', data=[])
    ], style={
        'maxWidth': '800px',
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
    prevent_initial_call=True
)
def update_chat(n_clicks, n_submit, user_input, chat_history_f):
    if not user_input:
        raise dash.exceptions.PreventUpdate

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

        
        chat_history_f.append({'role': 'user', 'message': user_input})
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
        
        if role == 'user':
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
            card = dbc.Card(dcc.Markdown(text, style={'whiteSpace': 'pre-wrap'}), style=style, body=True)
            avatar = html.Img(src=img_ai_path, style={"height": "40px", "borderRadius": "50%", "marginRight": "10px"})
            messages.append(html.Div([avatar, card], style={'display': 'flex', 'alignItems': 'start', 'justifyContent': 'flex-start'}))
        
    return messages

if __name__ == '__main__':
    app.run(host="0.0.0.0")