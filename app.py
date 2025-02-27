import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from io import BytesIO
import argparse
import os
import logging
import time
from datetime import timedelta

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebScraper:
    def __init__(self, url_inicial, profundidad_maxima=1, directorio_salida='resultados'):
        """
        Inicializa el scraper con la URL inicial, la profundidad máxima y el directorio de salida.
        
        Args:
            url_inicial: URL de inicio para el scraping
            profundidad_maxima: Niveles de profundidad a seguir desde la URL inicial
            directorio_salida: Directorio donde se guardará el PDF resultante
        """
        self.url_inicial = url_inicial
        self.profundidad_maxima = profundidad_maxima
        self.directorio_salida = directorio_salida
        self.urls_visitadas = set()
        self.datos_paginas = []
        
        # Variables para almacenar tiempos de ejecución
        self.tiempo_scraping = 0
        self.tiempo_pdf = 0
        self.tiempo_markdown = 0
        
        # Validar URL inicial
        if not self._es_url_valida(url_inicial):
            raise ValueError(f"URL inicial no válida: {url_inicial}")
        
        # Crear directorio de salida si no existe
        if not os.path.exists(directorio_salida):
            os.makedirs(directorio_salida)
    
    def _es_url_valida(self, url):
        """Verifica si una URL es válida."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def _es_mismo_dominio(self, url):
        """Verifica si una URL pertenece al mismo dominio que la URL inicial."""
        dominio_inicial = urlparse(self.url_inicial).netloc
        dominio_url = urlparse(url).netloc
        return dominio_inicial == dominio_url
    
    def _obtener_urls_pagina(self, soup, url_base):
        """Extrae todas las URLs de una página."""
        urls = []
        for enlace in soup.find_all('a', href=True):
            href = enlace['href']
            url_completa = urljoin(url_base, href)
            
            # Solo considerar URLs del mismo dominio
            if self._es_url_valida(url_completa) and self._es_mismo_dominio(url_completa):
                urls.append(url_completa)
        
        return urls
    
    def _extraer_contenido(self, soup, url):
        """
        Extrae el contenido relevante de una página.
        Puedes personalizar esta función según la estructura de las páginas que deseas scrapear.
        """
        titulo = soup.title.string if soup.title else "Sin título"
        
        # Extraer texto de párrafos
        parrafos = [p.get_text().strip() for p in soup.find_all('p') if p.get_text().strip()]
        
        # Extraer imágenes (URLs solamente)
        imagenes = []
        for img in soup.find_all('img', src=True):
            src = img['src']
            url_imagen = urljoin(url, src)
            if self._es_url_valida(url_imagen):
                imagenes.append(url_imagen)
        
        # Extraer encabezados
        encabezados = []
        for i in range(1, 7):
            for h in soup.find_all(f'h{i}'):
                texto = h.get_text().strip()
                if texto:
                    encabezados.append((i, texto))
        
        return {
            'url': url,
            'titulo': titulo,
            'encabezados': encabezados,
            'parrafos': parrafos,
            'imagenes': imagenes
        }
    
    def scrapear(self):
        """Realiza el scraping comenzando desde la URL inicial hasta la profundidad especificada."""
        tiempo_inicio = time.time()
        logger.info(f"Iniciando scraping desde {self.url_inicial} con profundidad {self.profundidad_maxima}")
        
        # Cola de URLs para procesar: (url, profundidad)
        cola = [(self.url_inicial, 0)]
        
        while cola:
            url_actual, profundidad_actual = cola.pop(0)
            
            # Saltar si ya visitamos esta URL o excede la profundidad máxima
            if url_actual in self.urls_visitadas or profundidad_actual > self.profundidad_maxima:
                continue
            
            logger.info(f"Procesando: {url_actual} (Profundidad: {profundidad_actual})")
            
            try:
                # Marcar como visitada
                self.urls_visitadas.add(url_actual)
                
                # Descargar y parsear la página
                respuesta = requests.get(url_actual, timeout=10)
                respuesta.raise_for_status()
                
                soup = BeautifulSoup(respuesta.text, 'html.parser')
                
                # Extraer contenido
                datos_pagina = self._extraer_contenido(soup, url_actual)
                self.datos_paginas.append(datos_pagina)
                
                # Si no hemos alcanzado la profundidad máxima, obtener enlaces para la siguiente profundidad
                if profundidad_actual < self.profundidad_maxima:
                    urls_encontradas = self._obtener_urls_pagina(soup, url_actual)
                    for url in urls_encontradas:
                        if url not in self.urls_visitadas:
                            cola.append((url, profundidad_actual + 1))
                
            except Exception as e:
                logger.error(f"Error al procesar {url_actual}: {str(e)}")
        
        tiempo_fin = time.time()
        tiempo_total = tiempo_fin - tiempo_inicio
        tiempo_formateado = str(timedelta(seconds=round(tiempo_total)))
        
        logger.info(f"Scraping completado. Se procesaron {len(self.urls_visitadas)} páginas en {tiempo_formateado}.")
        self.tiempo_scraping = tiempo_total
        return self.datos_paginas
    
    def generar_markdown(self, nombre_archivo_base):
        """Genera un archivo Markdown con los datos extraídos de las páginas."""
        if not self.datos_paginas:
            logger.warning("No hay datos para generar el archivo Markdown.")
            return False
        
        tiempo_inicio = time.time()
        
        # Crear nombre de archivo con extensión .md
        nombre_markdown = f"{os.path.splitext(nombre_archivo_base)[0]}.md"
        ruta_markdown = os.path.join(self.directorio_salida, nombre_markdown)
        
        try:
            with open(ruta_markdown, 'w', encoding='utf-8') as md_file:
                # Título del documento
                md_file.write("# Resultado del Scraping Web\n\n")
                
                # Información de parámetros
                md_file.write(f"- **URL inicial**: {self.url_inicial}\n")
                md_file.write(f"- **Profundidad máxima**: {self.profundidad_maxima}\n")
                md_file.write(f"- **Total de páginas procesadas**: {len(self.datos_paginas)}\n\n")
                
                # Agregar datos de cada página
                for i, pagina in enumerate(self.datos_paginas, 1):
                    md_file.write(f"## {i}. {pagina['titulo']}\n\n")
                    md_file.write(f"**URL**: {pagina['url']}\n\n")
                    
                    # Encabezados
                    if pagina['encabezados']:
                        for nivel, texto in pagina['encabezados']:
                            # Los encabezados en markdown son con # (nivel+1 porque ya usamos ## para el título de la página)
                            md_file.write(f"{'#' * (nivel+1)} {texto}\n\n")
                    
                    # Párrafos
                    for parrafo in pagina['parrafos']:
                        md_file.write(f"{parrafo}\n\n")
                    
                    # Imágenes
                    if pagina['imagenes']:
                        md_file.write("### Imágenes encontradas:\n\n")
                        
                        for url_img in pagina['imagenes']:
                            md_file.write(f"- {url_img}\n")
                        
                        md_file.write("\n")
                    
                    # Separador entre páginas
                    md_file.write("---\n\n")
            
            tiempo_fin = time.time()
            tiempo_total = tiempo_fin - tiempo_inicio
            tiempo_formateado = str(timedelta(seconds=round(tiempo_total)))
            
            logger.info(f"Archivo Markdown generado correctamente: {ruta_markdown} en {tiempo_formateado}")
            self.tiempo_markdown = tiempo_total
            return True
        
        except Exception as e:
            logger.error(f"Error al generar el archivo Markdown: {str(e)}")
            return False
    
    def generar_pdf(self, nombre_archivo='resultado_scraping.pdf'):
        """Genera un PDF con los datos extraídos de las páginas."""
        if not self.datos_paginas:
            logger.warning("No hay datos para generar el PDF.")
            return False
        
        tiempo_inicio = time.time()
        
        ruta_completa = os.path.join(self.directorio_salida, nombre_archivo)
        doc = SimpleDocTemplate(ruta_completa, pagesize=A4)
        
        # Estilos para el PDF
        estilos = getSampleStyleSheet()
        estilo_titulo = ParagraphStyle(
            'TituloPagina',
            parent=estilos['Heading1'],
            fontSize=18,
            spaceAfter=12,
            textColor=colors.darkblue
        )
        estilo_url = ParagraphStyle(
            'URL',
            parent=estilos['Normal'],
            fontSize=8,
            textColor=colors.gray
        )
        estilo_h = {
            1: ParagraphStyle('H1', parent=estilos['Heading1'], fontSize=16),
            2: ParagraphStyle('H2', parent=estilos['Heading2'], fontSize=14),
            3: ParagraphStyle('H3', parent=estilos['Heading3'], fontSize=12),
            4: ParagraphStyle('H4', parent=estilos['Heading4'], fontSize=11),
            5: ParagraphStyle('H5', parent=estilos['Heading5'], fontSize=10),
            6: ParagraphStyle('H6', parent=estilos['Heading6'], fontSize=9)
        }
        
        # Construir el contenido del PDF
        elementos = []
        
        # Título del documento
        elementos.append(Paragraph("Resultado del Scraping Web", estilos['Title']))
        elementos.append(Spacer(1, 20))
        
        # Información de parámetros del scraping
        elementos.append(Paragraph(f"URL inicial: {self.url_inicial}", estilos['Normal']))
        elementos.append(Paragraph(f"Profundidad máxima: {self.profundidad_maxima}", estilos['Normal']))
        elementos.append(Paragraph(f"Total de páginas procesadas: {len(self.datos_paginas)}", estilos['Normal']))
        elementos.append(Spacer(1, 20))
        
        # Agregar datos de cada página
        for i, pagina in enumerate(self.datos_paginas, 1):
            # Separador entre páginas
            if i > 1:
                elementos.append(Spacer(1, 30))
            
            # Título y URL de la página
            elementos.append(Paragraph(f"{i}. {pagina['titulo']}", estilo_titulo))
            elementos.append(Paragraph(f"URL: {pagina['url']}", estilo_url))
            elementos.append(Spacer(1, 10))
            
            # Encabezados
            if pagina['encabezados']:
                for nivel, texto in pagina['encabezados']:
                    elementos.append(Paragraph(texto, estilo_h[nivel]))
                    elementos.append(Spacer(1, 5))
            
            # Párrafos
            for parrafo in pagina['parrafos']:
                elementos.append(Paragraph(parrafo, estilos['Normal']))
                elementos.append(Spacer(1, 5))
            
            # Imágenes (hasta 3 por página para no sobrecargar el PDF)
            if pagina['imagenes']:
                elementos.append(Spacer(1, 10))
                elementos.append(Paragraph("Imágenes encontradas:", estilos['Heading4']))
                
                for url_img in pagina['imagenes'][:3]:
                    elementos.append(Paragraph(f"- {url_img}", estilos['Normal']))
                
                if len(pagina['imagenes']) > 3:
                    elementos.append(Paragraph(f"... y {len(pagina['imagenes']) - 3} imágenes más", estilos['Italic']))
        
        # Generar el PDF
        try:
            doc.build(elementos)
            
            tiempo_fin = time.time()
            tiempo_total = tiempo_fin - tiempo_inicio
            tiempo_formateado = str(timedelta(seconds=round(tiempo_total)))
            
            logger.info(f"PDF generado correctamente: {ruta_completa} en {tiempo_formateado}")
            self.tiempo_pdf = tiempo_total
            return True
        except Exception as e:
            logger.error(f"Error al generar el PDF: {str(e)}")
            return False
            
    def exportar_resultados(self, nombre_archivo='resultado_scraping.pdf'):
        """Exporta los resultados tanto en PDF como en Markdown."""
        resultado_pdf = self.generar_pdf(nombre_archivo)
        resultado_md = self.generar_markdown(nombre_archivo)
        
        return resultado_pdf and resultado_md

def main():
    # Configurar los argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Web Scraper con exportación a PDF')
    parser.add_argument('url', help='URL inicial para comenzar el scraping')
    parser.add_argument('-p', '--profundidad', type=int, default=1, help='Profundidad máxima de scraping (default: 1)')
    parser.add_argument('-o', '--output', default='resultados', help='Directorio de salida (default: resultados)')
    parser.add_argument('-f', '--filename', default='resultado_scraping.pdf', help='Nombre del archivo PDF (default: resultado_scraping.pdf)')
    
    args = parser.parse_args()
    
    try:
        # Crear e iniciar el scraper
        scraper = WebScraper(args.url, args.profundidad, args.output)
        scraper.scrapear()
        scraper.exportar_resultados(args.filename)
        
        nombre_base = os.path.splitext(args.filename)[0]
        
        # Convertir segundos a minutos:segundos
        tiempo_scraping_min = scraper.tiempo_scraping / 60
        tiempo_pdf_min = scraper.tiempo_pdf / 60
        tiempo_markdown_min = scraper.tiempo_markdown / 60
        tiempo_total_min = (scraper.tiempo_scraping + scraper.tiempo_pdf + scraper.tiempo_markdown) / 60
        
        # Formatear como minutos y segundos
        print("\n===== RESUMEN DE TIEMPOS =====")
        print(f"Tiempo de scraping: {tiempo_scraping_min:.2f} minutos")
        print(f"Tiempo de generación PDF: {tiempo_pdf_min:.2f} minutos")
        print(f"Tiempo de generación Markdown: {tiempo_markdown_min:.2f} minutos")
        print(f"TIEMPO TOTAL: {tiempo_total_min:.2f} minutos")
        print("=============================\n")
        
        print(f"Scraping completado.")
        print(f"PDF generado en: {os.path.join(args.output, args.filename)}")
        print(f"Markdown generado en: {os.path.join(args.output, nombre_base + '.md')}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    main()