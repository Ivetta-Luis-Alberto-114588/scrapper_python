python -m venv env

cd env

cd scritps

activate


pip **install** requests beautifulsoup4 reportlab

ctrl shift p --> select interpreter  --> seleccionar el interprete de python del entorno

python app.py https://ejemplo.com -p 2 -o carpeta_salida -f resultado.pdf




* `https://ejemplo.com` es la URL inicial
* `-p 2` establece la profundidad a 2 niveles (opcional, por defecto es 1)
* `-o carpeta_salida` establece el directorio de salida (opcional)
* `-f resultado.pdf` establece el nombre del archivo PDF (opcional)
