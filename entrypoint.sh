#!/bin/bash
set -e #exit on errors

#print statements as they are executed
[[ -n $DEBUG_ENTRYPOINT ]] && set -x

case ${1} in
  app:start)
    cd src && python run.py
    ;;
  app:help)
    echo "Available options:"
    echo " app:start        - Starts datalegend api (default)"
    echo " [command]        - Execute the specified command, eg. /bin/bash."
    ;;
  *)
    exec "$@"
    ;;
esac

exit 0
