#!/bin/bash

FUNCTION_ZIP=$PWD/function.zip

rm -f ${FUNCTION_ZIP}

zip -9 ${FUNCTION_ZIP} index.py

rm -rf package
mkdir package
pushd package
pip install requests --target .
zip -9rg ${FUNCTION_ZIP} .
popd
rm -rf package

aws lambda update-function-code --function-name MessageProcessor --zip-file fileb://${FUNCTION_ZIP}

rm -f ${FUNCTION_ZIP}
