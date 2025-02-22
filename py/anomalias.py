from flask import Flask, render_template
import firebase_admin
from firebase_admin import credentials, db
import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models
from sklearn.preprocessing import MinMaxScaler

# Inicializar o Firebase
cred = credentials.Certificate("path/to/your/firebase/credentials.json")
firebase_admin.initialize_app(cred, {'databaseURL': 'https://your-project.firebaseio.com'})

# Inicializar Flask
app = Flask(__name__)

# Função para buscar dados do Firebase
def get_data_from_firebase():
    ref = db.reference('sensor_data')  # Ajuste o caminho de acordo com seu banco
    data = ref.get()
    
    # Processar dados em um DataFrame
    df = pd.DataFrame(data)
    return df

# Função para construir e treinar o modelo Autoencoder
def train_autoencoder(data):
    scaler = MinMaxScaler()
    data_scaled = scaler.fit_transform(data)

    # Dividir dados em treinamento e teste
    train_size = int(0.8 * len(data_scaled))
    train_data = data_scaled[:train_size]
    test_data = data_scaled[train_size:]

    # Construir o Autoencoder
    model = models.Sequential([
        layers.Input(shape=(train_data.shape[1],)),
        layers.Dense(16, activation='relu'),
        layers.Dense(8, activation='relu'),
        layers.Dense(16, activation='relu'),
        layers.Dense(train_data.shape[1], activation='sigmoid')
    ])
    
    model.compile(optimizer='adam', loss='mse')
    model.fit(train_data, train_data, epochs=50, batch_size=32, validation_data=(test_data, test_data))

    # Calcular erro de reconstrução para determinar o limiar
    train_predictions = model.predict(train_data)
    train_mse = np.mean(np.power(train_data - train_predictions, 2), axis=1)
    threshold = np.percentile(train_mse, 95)  # Limiar baseado no erro de reconstrução (95% percentil)

    return model, scaler, threshold, test_data

# Função para detectar anomalias nos dados
def detect_anomalies(model, scaler, threshold, data):
    data_scaled = scaler.transform(data)
    predictions = model.predict(data_scaled)
    mse = np.mean(np.power(data_scaled - predictions, 2), axis=1)
    anomalies = mse > threshold
    return mse, anomalies

# Rota principal da aplicação
@app.route('/')
def index():
    # Buscar dados do Firebase
    df = get_data_from_firebase()
    
    # Supondo que a coluna 'flow_rate' contém os dados de fluxo de água
    flow_data = df[['flow_rate']].values

    # Treinar o Autoencoder e detectar anomalias
    model, scaler, threshold, _ = train_autoencoder(flow_data)
    mse, anomalies = detect_anomalies(model, scaler, threshold, flow_data)

    # Gerar o resultado para exibir no HTML
    results = []
    for i in range(len(df)):
        results.append({
            'index': i,
            'flow_rate': df.iloc[i]['flow_rate'],
            'mse': mse[i],
            'anomaly': 'Sim' if anomalies[i] else 'Não'
        })
    
    # Renderizar o template result.html e passar os dados
    return render_template('result.html', results=results)

# Rodar a aplicação Flask
if __name__ == '__main__':
    app.run(debug=True)
