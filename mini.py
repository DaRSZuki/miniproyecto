import matplotlib
matplotlib.use('Agg')  # Configurar matplotlib en modo no interactivo
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
import os
import numpy as np
import soundfile as sf
import matplotlib.pyplot as plt
import io
import base64
import time
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max upload
app.config['ALLOWED_EXTENSIONS'] = {'wav'}
app.secret_key = 'clave_super_secreta'

# Crear carpeta de uploads si no existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Sesión de archivos (simulada en memoria para este ejemplo)
SESSION_FILES = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    session_id = request.form.get('session_id', str(uuid.uuid4()))
    
    # Inicializar sesión si no existe
    if session_id not in SESSION_FILES:
        SESSION_FILES[session_id] = []
    
    # Verificar que no hay más de 10 archivos
    if len(SESSION_FILES[session_id]) >= 10:
        return jsonify({
            'success': False,
            'message': 'Ya has subido el máximo de 10 archivos. Elimina alguno para continuar.'
        })
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No se seleccionó ningún archivo'})
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No se seleccionó ningún archivo'})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")
        file.save(file_path)
        
        # Obtener info del archivo de audio
        try:
            info = sf.info(file_path)
            file_info = {
                'id': file_id,
                'filename': filename,
                'path': file_path,
                'duration': round(info.duration, 2),
                'samplerate': info.samplerate,
                'channels': info.channels
            }
            SESSION_FILES[session_id].append(file_info)
            
            return jsonify({
                'success': True,
                'message': 'Archivo subido correctamente',
                'file_info': file_info,
                'session_id': session_id,
                'files': SESSION_FILES[session_id]
            })
        except Exception as e:
            os.remove(file_path)
            return jsonify({'success': False, 'message': f'Error al procesar el archivo: {str(e)}'})
    
    return jsonify({'success': False, 'message': 'Tipo de archivo no permitido'})

@app.route('/files', methods=['GET'])
def get_files():
    session_id = request.args.get('session_id', '')
    if session_id in SESSION_FILES:
        return jsonify({'success': True, 'files': SESSION_FILES[session_id]})
    return jsonify({'success': False, 'message': 'Sesión no encontrada', 'files': []})

@app.route('/delete/<session_id>/<file_id>', methods=['DELETE'])
def delete_file(session_id, file_id):
    if session_id in SESSION_FILES:
        for i, file_info in enumerate(SESSION_FILES[session_id]):
            if file_info['id'] == file_id:
                try:
                    os.remove(file_info['path'])
                except:
                    pass  # Ignorar errores al eliminar
                SESSION_FILES[session_id].pop(i)
                return jsonify({'success': True, 'message': 'Archivo eliminado correctamente'})
    
    return jsonify({'success': False, 'message': 'Archivo no encontrado'})

@app.route('/play/<session_id>/<file_id>', methods=['GET'])
def play_file(session_id, file_id):
    if session_id in SESSION_FILES:
        for file_info in SESSION_FILES[session_id]:
            if file_info['id'] == file_id:
                return send_from_directory(os.path.dirname(file_info['path']), 
                                         os.path.basename(file_info['path']),
                                         as_attachment=False)
    
    return jsonify({'success': False, 'message': 'Archivo no encontrado'})

@app.route('/process', methods=['POST'])
def process_audio():
    data = request.json
    session_id = data.get('session_id')
    file_id = data.get('file_id')
    operation = data.get('operation')
    
    if not session_id or not file_id or not operation:
        return jsonify({'success': False, 'message': 'Parámetros incompletos'})
    
    file_info = None
    for file in SESSION_FILES.get(session_id, []):
        if file['id'] == file_id:
            file_info = file
            break
    
    if not file_info:
        return jsonify({'success': False, 'message': 'Archivo no encontrado'})
    
    try:
        audio_path = file_info['path']
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], f"processed_{uuid.uuid4()}_{os.path.basename(audio_path)}")
        
        # Cargar el audio
        x, fs = sf.read(audio_path, dtype='float32')
        
        if operation == 'reverse':
            # Procesar el audio en reversa
            processed_audio = np.flip(x)
            sf.write(output_path, processed_audio, fs)
            operation_name = "Audio Invertido"
        
        elif operation == 'amplify':
            # Aumentar amplitud en 50%
            factor = data.get('factor', 1.5)
            processed_audio = x * factor
            processed_audio = np.clip(processed_audio, -1, 1)  # Evitar clipping
            sf.write(output_path, processed_audio, fs)
            operation_name = f"Amplitud modificada ({factor}x)"
        
        elif operation == 'change_speed':
            # Cambiar velocidad (simular cambiando la tasa de muestreo)
            speed_factor = data.get('speed_factor', 1.0)
            new_fs = int(fs * speed_factor)
            sf.write(output_path, x, new_fs)
            operation_name = f"Velocidad modificada ({speed_factor}x)"
        
        elif operation == 'extract_segment':
            # Extraer segmento
            start_sec = data.get('start_sec', 0)  # Segundo inicial
            duration_sec = data.get('duration_sec', 5)  # Duración del segmento

            # Validar que la duración no exceda la longitud restante del archivo
            max_duration = sf.info(audio_path).duration - start_sec
            if duration_sec > max_duration:
                return jsonify({
                    'success': False,
                    'message': f'La duración solicitada excede la longitud restante del archivo. Duración máxima: {max_duration:.2f} segundos.'
                })

            # Calcular muestras de inicio y fin
            start_sample = int(fs * start_sec)
            end_sample = int(start_sample + fs * duration_sec)

            # Asegurarse de que no exceda la longitud del archivo
            if end_sample > len(x):
                end_sample = len(x)

            # Extraer el segmento
            segment = x[start_sample:end_sample]

            # Guardar el segmento extraído
            sf.write(output_path, segment, fs)
            operation_name = f"Segmento ({start_sec}s - {start_sec + duration_sec}s)"
        
        elif operation == 'swap_channels':
            # Intercambiar canales (solo si es estéreo)
            if len(x.shape) >= 2 and x.shape[1] >= 2:
                processed_audio = x.copy()
                processed_audio[:, 0], processed_audio[:, 1] = x[:, 1], x[:, 0]
                sf.write(output_path, processed_audio, fs)
                operation_name = "Canales intercambiados"
            else:
                return jsonify({'success': False, 'message': 'El archivo no es estéreo'})
        
        elif operation == 'change_sample_rate':
            # Cambiar la frecuencia de muestreo
            new_sample_rate = data.get('sample_rate', 44100)
            if new_sample_rate <= 0:
                return jsonify({'success': False, 'message': 'La frecuencia de muestreo debe ser mayor que 0'})
            
            # Reescribir el archivo con la nueva frecuencia de muestreo
            sf.write(output_path, x, new_sample_rate)
            operation_name = f"Frecuencia de muestreo cambiada a {new_sample_rate} Hz"
        
        else:
            return jsonify({'success': False, 'message': 'Operación no reconocida'})
        
        # Crear nuevo archivo en la sesión
        new_file_id = str(uuid.uuid4())
        new_filename = f"{operation_name}_{os.path.basename(audio_path)}"
        
        new_file_info = {
            'id': new_file_id,
            'filename': new_filename,
            'path': output_path,
            'duration': sf.info(output_path).duration,
            'samplerate': sf.info(output_path).samplerate,
            'channels': sf.info(output_path).channels,
            'processed': True,
            'original_id': file_id,
            'operation': operation
        }
        
        SESSION_FILES[session_id].append(new_file_info)
        
        return jsonify({
            'success': True, 
            'message': 'Audio procesado correctamente',
            'file_info': new_file_info
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al procesar el audio: {str(e)}'})

@app.route('/visualize/<session_id>/<file_id>', methods=['GET'])
def visualize_audio(session_id, file_id):
    if session_id in SESSION_FILES:
        for file_info in SESSION_FILES[session_id]:
            if file_info['id'] == file_id:
                try:
                    # Cargar el audio
                    x, fs = sf.read(file_info['path'], dtype='float32')
                    
                    # Si es estéreo, promediamos los canales para la visualización
                    if len(x.shape) > 1 and x.shape[1] > 1:
                        x = np.mean(x, axis=1)
                    
                    # Limitar a 10 segundos o menos para la visualización
                    max_samples = min(len(x), 10 * fs)
                    if max_samples < len(x):
                        x = x[:max_samples]
                    
                    # Crear la figura
                    plt.figure(figsize=(10, 4))
                    plt.plot(np.arange(len(x)) / fs, x)
                    plt.title(f'Forma de onda: {file_info["filename"]}')
                    plt.xlabel('Tiempo (s)')
                    plt.ylabel('Amplitud')
                    plt.grid(True)
                    
                    # Convertir figura a imagen en base64
                    buf = io.BytesIO()
                    plt.savefig(buf, format='png')
                    plt.close()
                    buf.seek(0)
                    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
                    
                    return jsonify({
                        'success': True, 
                        'waveform': img_base64,
                        'duration': file_info['duration'],
                        'samplerate': file_info['samplerate']
                    })
                    
                except Exception as e:
                    return jsonify({'success': False, 'message': f'Error al visualizar el audio: {str(e)}'})
    
    return jsonify({'success': False, 'message': 'Archivo no encontrado'})

if __name__ == '__main__':
    app.run(debug=True)