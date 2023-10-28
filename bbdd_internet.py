import time
import datetime
import json
import http.client
import io
import gzip
import random
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

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
            formatted_date_time = fecha_hora_actual.strftime("%Y-%m-%dT%H:%M:%S")
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
   
    
    while True:
    
        api_key = 'f4498315-666b-3d76-9e7c-7240775f96d2'
    
        component_id = "precios"
        compress = True
        url = '/api/feed'
    
        conn = http.client.HTTPConnection('www.grovestreams.com')
    
        precio_oro, timestamp = obtener_precio_y_tiempo()

        if precio_oro is not None and timestamp is not None:
            samples = [
                {'compId': component_id, 'streamId': 'precio_oro', 'data': precio_oro},
                {'compId': component_id, 'streamId': 'timestamp', 'data': timestamp}
            ]
            
            json_encoded = json.dumps(samples)

            try:
                if compress:
                    body = gzip.compress(json_encoded.encode('utf-8'))
                    print('Compressed feed ' + str(100 * len(body) / len(json_encoded)) + '%')

                    headers = {
                        "Content-Encoding": "gzip",
                        "Connection": "close",
                        "Content-type": "application/json",
                        "Cookie": "api_key=" + api_key
                    }
                else:
                    body = json_encoded
                    headers = {
                        "Connection": "close",
                        "Content-type": "application/json",
                        "Cookie": "org=" + org + ";api_key=" + api_key
                    }

                print('Uploading feed to: ' + url)

                conn.request("PUT", url, body, headers)
                response = conn.getresponse()
                status = response.status

              

            except Exception as e:
                print('HTTP Failure: ' + str(e))
            finally:
                if conn is not None:
                    conn.close()

            time.sleep(120)

