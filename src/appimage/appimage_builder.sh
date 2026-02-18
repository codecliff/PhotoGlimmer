#APP_VER=$(sed -n 's/^APP_VERSION.*=.*["'\'']\([^"'\'']*\)["'\''].*/\1/p' ../photoglimmer/backend/Interfaces.py)
#echo $APP_VER 
#export APP_VERSION=$APP_VER 
python -m venv appimage_venv
source appimage_venv/bin/activate
pip install appimage-builder
pip install packaging==20.9
appimage-builder --recipe AppImageBuilder.yml

