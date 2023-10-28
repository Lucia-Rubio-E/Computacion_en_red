import time  								# biblioteca de tiempo
from datetime import datetime as dt  					# biblio de fecha y hora
import re    								# biblio expresiones regulares
from bs4 import BeautifulSoup						# para el análisis de HTML

from selenium import webdriver  					# importa selenium
from selenium.webdriver.chrome.options import Options  			# opciones navegador chrome
from selenium.webdriver.common.by import By 				# para localización de elementos
from selenium.webdriver.support.ui import WebDriverWait 		# espera explícita de selenium
from selenium.webdriver.support import expected_conditions as EC 	# espera de las condiciones de selenium
from elasticsearch import Elasticsearch					# importa elasticsearch para la bbddlocal

def create_node_config(scheme, host, port):
    return {
        'scheme': scheme,
        'host': host,
        'port': port
    }

# Crear la configuración del nodo para Elasticsearch
node_config = create_node_config('http', 'localhost', 9200)

# Configuración de la conexión a Elasticsearch
es = Elasticsearch([node_config])

def obtener_precio_y_tiempo():						# obtener el precio del oro y la hora actual

    try:								# configuramos el navegador para ejecutarse en modo headless
        options = Options()
        options.add_argument('--headless')
        driver = webdriver.Chrome(options=options)
        driver.get('https://es.investing.com/commodities/gold')
									# espera hasta que se cargue el elemento con el ID '__next'
        wait = WebDriverWait(driver, 1)
        wait.until(EC.presence_of_element_located((By.ID, '__next')))
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
									# busca el precio del oro en el HTML con expresiones regulares
        precio_oro_match = re.search(r'text-5xl[^>]*>([^<]+)<', str(soup))
        precio_oro = precio_oro_match.group(1).replace('.', '').replace(',', '.').strip() if precio_oro_match else None

        if precio_oro: 							# obtenemos la fecha y hora actual
            fecha_hora_actual = dt.now()
            formatted_date_time = fecha_hora_actual.strftime("%Y-%m-%dT%H:%M:%S")
            return float(precio_oro.replace(',', '.')), formatted_date_time
        else:
            print('No se encontró el elemento div con la clase text-5xl.')
            return None, None

    except Exception as e:
        print(f"Error al obtener el precio y tiempo: {e}")
        return None, None
    finally: 								# cierra el navegador
        driver.quit()


while True:								# bucle infinito para obtener y subir datos continuamente
    precio_oro, timestamp = obtener_precio_y_tiempo()

    if precio_oro is not None and timestamp is not None:
        doc = {"gold_price": precio_oro, "timestamp": timestamp}# crea un doc con el precio del oro y la fecha y hora actual
        es.index(index='datos_oro', body=doc)
        es.indices.refresh(index='datos_oro')				# refresca el índice en elasticsearch
        print(f'Dato subido: {doc}')					# imprime un mensaje indicando que se ha subido un dato
        time.sleep(120)							# cada 120segundos
        
        
        

    
        
