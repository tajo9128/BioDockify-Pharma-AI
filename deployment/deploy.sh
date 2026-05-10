#!/bin/bash
# BioDockify v2.0.0 Deployment Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    print_success "Docker is installed"
}

# Check if Docker Compose is installed
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    print_success "Docker Compose is installed"
}

# Check if Bun is installed
check_bun() {
    if ! command -v bun &> /dev/null; then
        print_error "Bun is not installed. Please install Bun first."
        exit 1
    fi
    print_success "Bun is installed"
}

# Start Docker services
start_docker_services() {
    print_info "Starting Docker services..."

    # Build and start services
    docker-compose up -d

    print_success "Docker services started"
}

# Wait for service to be healthy
wait_for_service() {
    local service_name=$1
    local max_attempts=30
    local attempt=1

    print_info "Waiting for $service_name to be ready..."

    while [ $attempt -le $max_attempts ]; do
        if docker-compose ps | grep -q "$service_name.*healthy"; then
            print_success "$service_name is ready"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done

    print_error "$service_name failed to become healthy"
    return 1
}

# Pull Ollama model
pull_ollama_model() {
    print_info "Pulling Ollama model (llama3.2)..."

    docker-compose exec -T ollama ollama pull llama3.2

    print_success "Ollama model pulled"
}

# Initialize Neo4j database
initialize_neo4j() {
    print_info "Waiting for Neo4j to initialize..."
    sleep 10

    print_success "Neo4j initialized"
}

# Install dependencies
install_dependencies() {
    print_info "Installing project dependencies..."
    bun install
    print_success "Dependencies installed"
}

# Push database schema
push_database_schema() {
    print_info "Pushing database schema..."
    bun run db:push
    print_success "Database schema pushed"
}

# Verify services are running
verify_deployment() {
    print_info "Verifying deployment..."

    # Check GROBID
    if curl -f http://localhost:8070/api/version &> /dev/null; then
        print_success "GROBID service is accessible"
    else
        print_warning "GROBID service may not be fully ready yet"
    fi

    # Check Neo4j
    if curl -f http://localhost:7474 &> /dev/null; then
        print_success "Neo4j service is accessible"
    else
        print_warning "Neo4j service may not be fully ready yet"
    fi

    # Check Ollama
    if curl -f http://localhost:11434/api/tags &> /dev/null; then
        print_success "Ollama service is accessible"
    else
        print_warning "Ollama service may not be fully ready yet"
    fi
}

# Show deployment summary
show_summary() {
    echo ""
    print_success "BioDockify v2.0.0 Deployment Complete!"
    echo ""
    print_info "Services:"
    echo "  • Frontend (Next.js): http://localhost:3000"
    echo "  • GROBID: http://localhost:8070"
    echo "  • Neo4j Browser: http://localhost:7474"
    echo "  • Neo4j Bolt: bolt://localhost:7687"
    echo "  • Ollama API: http://localhost:11434"
    echo ""
    print_info "Docker Commands:"
    echo "  • View logs: docker-compose logs -f"
    echo "  • Stop services: docker-compose down"
    echo "  • Restart services: docker-compose restart"
    echo "  • Check status: docker-compose ps"
    echo ""
    print_info "Development Commands:"
    echo "  • Start dev server: bun run dev"
    echo "  • Run linter: bun run lint"
    echo "  • Build project: bun run build"
    echo ""
}

# Main deployment flow
main() {
    echo ""
    print_info "BioDockify v2.0.0 Deployment Script"
    echo "========================================"
    echo ""

    # Pre-flight checks
    print_info "Running pre-flight checks..."
    check_docker
    check_docker_compose
    check_bun
    echo ""

    # Install dependencies
    install_dependencies
    echo ""

    # Push database schema
    push_database_schema
    echo ""

    # Start Docker services
    start_docker_services
    echo ""

    # Wait for services to be healthy
    wait_for_service "grobid"
    wait_for_service "neo4j"
    wait_for_service "ollama"
    echo ""

    # Initialize Neo4j
    initialize_neo4j
    echo ""

    # Pull Ollama model
    pull_ollama_model
    echo ""

    # Verify deployment
    verify_deployment
    echo ""

    # Show summary
    show_summary
}

# Run main function
main "$@"
