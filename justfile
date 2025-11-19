default:
    just build
build:
    export BUILDX_NO_DEFAULT_ATTESTATIONS=1
    docker buildx build --force-rm --provenance false --platform linux/amd64,linux/arm64 --push -t hubd.diasoft.ru/offer-generator:latest .