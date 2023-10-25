from flask import Flask, render_template, request,redirect, url_for, Response
from bs4 import BeautifulSoup
import time
from elasticsearch import Elasticsearch
import requests
import datetime
import json
import asyncio 					# biblio de fecha y hora
import re    								# biblio expresiones regulares

from selenium import webdriver  					# importa selenium
from selenium.webdriver.chrome.options import Options  			# opciones navegador chrome
from selenium.webdriver.common.by import By 				# para localización de elementos
from selenium.webdriver.support.ui import WebDriverWait 		# espera explícita de selenium
from selenium.webdriver.support import expected_conditions as EC 	# espera de las condiciones de selenium

import hashlib

app = Flask(__name__)				# inicio la app de flask
						# variables globales
mi_variable1 = "Último valor: "				#variables para mostrar en el html
mi_variable2 = "Usuario registrado "
mi_variable3 = "Sesión con el usuario "
mi_variable4 ="El usuario ya está registrado "
mi_variable5="Contraseña incorrecta"
mi_variable6="El usuario no existe"
mi_variable7=None
blanco = "   "
usuario = None
datoglobal = None

mediaoro_local=0
mediaoro_internet=0
contador=0

						# conectamos con elasticsearch
es = Elasticsearch([{'host': 'localhost', 'port': 9200}])
index_usuarios = 'usuarios_indice'

umbral1 = 0
umbral2 = 0
umbral_actual = None
umbral_historico=None
dato_actual = None
dato_anterior = None
fecha_actual = None
contador2=0
ultimos_valores = []
ultimo_valor_1=0
ultimo_valor_2=0
ultimo_valor_3=0
ultimo_valor_4=0
ultimo_valor_5=0



def calcular_media_oro_local():			# se calcula la media del oro de la base de datos local

    result = es.search(index= 'datos_oro', body={"query": {"match_all": {}}},size = 1000)

    totalpreciooro = 0
    num = len(result['hits']['hits'])

    for hit in result['hits']['hits']:
        precio_oro = hit['_source']['gold_price']
        totalpreciooro += precio_oro


    media = totalpreciooro / num if num > 0 else 0
    media=round(media,2)
    return media

    
def calcular_media_oro_internet():
    api_key = 'f4498315-666b-3d76-9e7c-7240775f96d2'
    compId = "precios"
    streamId = "precio_oro"
    
    urlBase = "https://grovestreams.com/api/"
    url = f"{urlBase}comp/{compId}/stream/{streamId}/feed?api_key={api_key}"
    response = requests.get(url)    
    json = response.json()
    #print(str(json))
    
    # Comprobar si la solicitud fue exitosa
    if response.status_code == 200:
        try:
            data = response.json()
        except Exception as e:
            print(f"Error al decodificar la respuesta JSON: {e}")
            return None

        # Verificar si hay datos en la respuesta
        if data:
            valores = [punto['data'] for punto in data]
            media = sum(valores) / len(valores)
            return round(media, 2)
        else:
            print("La respuesta no contiene datos.")
    else:
        print(f"Error en la solicitud HTTP. Código de estado: {response.status_code}")
    
    return None



@app.route('/', methods=['GET', 'POST'])
def menupp():
    global mediaoro_local, mediaoro_internet, usuario, datoglobal
    fechahora2=0
    
    if request.method == 'POST':
        accion = request.form.get('accion')
        usuario = request.form.get('usuario')
        
        password2 = request.form.get('password')
        password_bytes = password2.encode()

        password = hashlib.md5(password_bytes).hexdigest()
        mediaoro_local = calcular_media_oro_local()
        mediaoro_internet = calcular_media_oro_internet()
        
        if accion == 'registro':
            if usuario is not None and password is not None:
                datos_usuario = {'usuario': usuario, 'password': password}

                try:
                    if not es.indices.exists(index=index_usuarios):
                        es.indices.create(index=index_usuarios)

                    consulta_usuario = {"query": {"match_all": {}}}
                    resultado_usuario = es.search(index=index_usuarios, body=consulta_usuario, size=1000)

                    for hit in resultado_usuario['hits']['hits']:
                        usuario_extraido = hit['_source']['usuario']
                        if usuario_extraido == usuario:
                            print(f'El usuario ya está registrado')
                            return render_template('registro.html', mi_variable=mi_variable4)
                        
                    print(f'El usuario NO está ya registrado, se va a registrar')
                    es.index(index=index_usuarios, doc_type='_doc', body=datos_usuario)
                    es.indices.refresh(index=index_usuarios)
                    print(f'Documento indexado en Elasticsearch: {datos_usuario}')
                    print(f'El usuario: {usuario} se ha registrado con la Contraseña: {password}')
               
                    return render_template('menupp.html', mi_variable=mi_variable2, media_local=mediaoro_local, media_internet=mediaoro_internet, contador=contador,idusuario=usuario,mostrar_clase=True, ultimovalor=blanco)
                    
                except Exception as e:
                    print(f"Error al indexar en Elasticsearch: {e}")

                

        elif accion == 'login':
            user_query = {"query": {"term": {"usuario": usuario}}}
            user_result = es.search(index=index_usuarios, body=user_query, size=1)
        
            for hit in user_result['hits']['hits']:
                usuario_extraido = hit['_source']['usuario']
                usuario_extraido_password = hit['_source']['password']
            
                if usuario_extraido_password == password:
                    
                    print(f'Usuario para login: {usuario} , password: {password} ')
                    
                    return render_template('menupp.html', mi_variable=mi_variable3, media_local=mediaoro_local, media_internet=mediaoro_internet, contador=contador,idusuario=usuario,mostrar_clase=True, ultimovalor=blanco)
                    

                else:
                    print(f'Contraseña incorrecta')
                    return render_template('entrada.html', mi_variable=mi_variable5)

            else:
                print(f'Usuario no encontrado')
                return render_template('entrada.html', mi_variable=mi_variable6)


    else:	#si la solicitud no es POST (es GET)
	
        datoglobal,fechahora2=obtener_precio_y_tiempo()
                
    return render_template('menupp.html', mi_variable=mi_variable1, idusuario=blanco, ultimovalor=datoglobal, mostrar_clase=False,media_local=mediaoro_local,media_internet=0)

@app.route('/registro')			#ruta para mostrar el formulario de registro (y vaya a registro.html)
def registro():
    return render_template('registro.html')

@app.route('/entrada')			#ruta para mostrar el formulario de entrada (y vaya a entrada.html)
def entrada():
    return render_template('entrada.html')

@app.route('/salida')			#ruta para mostrar el formulario de salida (y vaya a salida.html)
def salida():
    return render_template('salida.html')

@app.route('/media_lo', methods=['POST'])	#ruta para pedir la media de la bbdd local
def media_loc():
    global mediaoro_local, contador 
    mediaoro_local = calcular_media_oro_local()
    contador += 1					#sumamos uno al contador de la cuenta de las solicitudes de la media de las bbdds
    return render_template('menupp.html', media_local=mediaoro_local,media_internet=mediaoro_internet, contador=contador,idusuario=usuario,mostrar_clase=True,ultimo_valor_1=ultimo_valor_1, ultimo_valor_2=ultimo_valor_2, ultimo_valor_3=ultimo_valor_3, ultimo_valor_4=ultimo_valor_4, ultimo_valor_5=ultimo_valor_5)

@app.route('/media_int', methods=['POST'])	#ruta para pedir la media de la bbdd de internet
def media_int():
    global mediaoro_internet, contador
    mediaoro_internet = calcular_media_oro_internet()  
    contador += 1  					#sumamos uno al contador de la cuenta de las solicitudes de la media de las bbdds
    return render_template('menupp.html', media_local=mediaoro_local, media_internet=mediaoro_internet, contador=contador,idusuario=usuario,mostrar_clase=True,ultimo_valor_1=ultimo_valor_1, ultimo_valor_2=ultimo_valor_2, ultimo_valor_3=ultimo_valor_3, ultimo_valor_4=ultimo_valor_4, ultimo_valor_5=ultimo_valor_5)
    
@app.route('/graficas', methods=['POST'])	#ruta para que se muestre las gráficas (y vaya a graficas.html)
def graficas_externas():
    return render_template('graficas.html')
  
@app.route('/vuelvemenu', methods=['POST'])	#ruta para volver al menú principal desde graficas.html, y vaya a menupp.html
def vuelve_menu():
    return render_template('menupp.html', media_local=mediaoro_local, media_internet=mediaoro_internet, contador=contador,idusuario=usuario,mostrar_clase=True)
  

@app.route('/umbral_historico', methods=['POST'])
def procesar_umbral_historico():
    global umbral1
    umbral1 = float(request.form['umbral_historico'])

    api_key = 'f4498315-666b-3d76-9e7c-7240775f96d2'
    compId = "precios"
    streamId = "precio_oro"
    
    urlBase = "https://grovestreams.com/api/"
    url = f"{urlBase}comp/{compId}/stream/{streamId}/feed?api_key={api_key}"
    response = requests.get(url)    
    data = response.json()
    #print(str(data))
    

    data = response.json()
    valores_superiores = [punto['data'] for punto in data if punto['data'] > umbral1]

    global ultimo_valor_1, ultimo_valor_2, ultimo_valor_3, ultimo_valor_4, ultimo_valor_5
    global dato_actual, fecha_actual
    dato_actual, fecha_hora = obtener_precio_y_tiempo()
   
    
    if len(valores_superiores) >= 5:
        ultimo_valor_1 = valores_superiores[-1]
        ultimo_valor_2 = valores_superiores[-2]
        ultimo_valor_3 = valores_superiores[-3]
        ultimo_valor_4 = valores_superiores[-4]
        ultimo_valor_5 = valores_superiores[-5]
        print('SÍ hay suficientes valores para mostrar')
        
    else:
        print('NO hay suficientes valores para mostrar')
        
    return render_template('menupp.html', umbral_historico=umbral1, media_local=mediaoro_local, media_internet=mediaoro_internet, contador=contador, idusuario=usuario, mostrar_clase=True, ultimo_valor_1=ultimo_valor_1, ultimo_valor_2=ultimo_valor_2, ultimo_valor_3=ultimo_valor_3, ultimo_valor_4=ultimo_valor_4, ultimo_valor_5=ultimo_valor_5)



@app.route('/umbral_actual', methods=['POST'])
def procesar_umbral_actual():
    global umbral2
    umbral2 = float(request.form['umbral_actual'])
    
    
    global dato_actual, fecha_actual
    dato_actual, fecha_hora = obtener_precio_y_tiempo()
   
        
    return render_template('menupp.html', umbral_actual=umbral2, media_local=mediaoro_local, media_internet=mediaoro_internet, contador=contador, idusuario=usuario, mostrar_clase=True, ultimo_valor_1=ultimo_valor_1, ultimo_valor_2=ultimo_valor_2, ultimo_valor_3=ultimo_valor_3, ultimo_valor_4=ultimo_valor_4, ultimo_valor_5=ultimo_valor_5)


@app.route('/notifications')
def sse_notifications():
    
    def event_stream():
        global dato_actual
        while True:
            precio2, fecha_hora = obtener_precio_y_tiempo()
            if umbral2 is not None:
                if precio2 > umbral2 and precio2 != dato_actual:
                    dato_actual = precio2
                    yield f"data: Umbral superado\n\n"  
                else:
                    yield f"data: {fecha_hora}: {dato_actual}\n\n"
    return Response(event_stream(), content_type='text/event-stream')



def obtener_precio_y_tiempo():
    url = 'https://es.investing.com/commodities/gold'

    try:
        options = Options()
        options.add_argument('--headless')
        driver = webdriver.Chrome(options=options)
        driver.get(url)

        wait = WebDriverWait(driver, 1)
        wait.until(EC.presence_of_element_located((By.ID, '__next')))
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        precio_oro_match = re.search(r'text-5xl[^>]*>([^<]+)<', str(soup))
        precio_oro = precio_oro_match.group(1).replace('.', '').replace(',', '.').strip() if precio_oro_match else None

        if precio_oro:
            fecha_hora_actual = datetime.datetime.now()
            formatted_date_time = fecha_hora_actual.strftime("%Y-%m-%d %H:%M:%S")
            return float(precio_oro.replace(',', '.')), formatted_date_time
        else:
            print('No se encontró el elemento div con la clase text-5xl.')
            return None, None

    except Exception as e:
        print(f"Error al obtener el precio y tiempo: {e}")
        return None, None
    finally:
        driver.quit()


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)






