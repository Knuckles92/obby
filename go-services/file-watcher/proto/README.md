# Protocol Buffer Generation

To generate Go code from the `.proto` files, install Protocol Buffers compiler:

## Windows
1. Download from https://github.com/protocolbuffers/protobuf/releases
2. Extract and add to PATH
3. Or use Chocolatey: `choco install protoc`

## Generate Code
```bash
protoc --go_out=. --go-grpc_out=. --go_opt=paths=source_relative --go-grpc_opt=paths=source_relative proto/file_watcher.proto
```

This will generate files in `proto/generated/` directory.

