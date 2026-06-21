package main

import "fmt"

type Server struct {
	Port int
	Host string
}

type Handler interface {
	Handle(path string) string
}

func NewServer(port int, host string) *Server {
	return &Server{Port: port, Host: host}
}

func (s *Server) Start() error {
	fmt.Printf("Starting on %s:%d\n", s.Host, s.Port)
	return nil
}

func (s *Server) Stop() {
	fmt.Println("Stopping server")
}

func healthHandler(path string) string {
	return "OK"
}

func main() {
	s := NewServer(8080, "localhost")
	s.Start()
}
