#!/bin/bash
set -e

get_version() {
  date '+%y%m%d_%H%M'
}

if [[ -z "$dock_version" ]]; then
    dock_version=$(get_version)
fi

echo "Building image verion:$dock_version"

docker build . -t image-server

docker tag image-server mustakimali/private:image-server-latest
docker push mustakimali/private:image-server-latest

tag="mustakimali/private:image-server-$dock_version"
docker tag image-server $tag
docker push mustakimali/private:image-server-$dock_version

docker rmi image-server
docker rmi mustakimali/private:image-server-latest

echo "Tagged mustakimali/private:image-server-$dock_version"

kubectl -n image-server set image deployments/image-server image-server=mustakimali/private:image-server-${dock_version}
kubectl -n image-server rollout status deployments/image-server -w

echo "Version: $dock_version"
