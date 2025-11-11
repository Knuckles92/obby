package tracker

import (
	"context"
	"sync"
)

// Task represents a work item
type Task interface {
	Execute(ctx context.Context) error
}

// WorkerPool manages a pool of workers for concurrent processing
type WorkerPool struct {
	workers   int
	taskQueue chan Task
	wg        sync.WaitGroup
	ctx       context.Context
	cancel    context.CancelFunc
}

// NewWorkerPool creates a new worker pool
func NewWorkerPool(workers int) *WorkerPool {
	ctx, cancel := context.WithCancel(context.Background())
	return &WorkerPool{
		workers:   workers,
		taskQueue: make(chan Task, workers*2),
		ctx:       ctx,
		cancel:    cancel,
	}
}

// Start starts the worker pool
func (wp *WorkerPool) Start() {
	for i := 0; i < wp.workers; i++ {
		wp.wg.Add(1)
		go wp.worker()
	}
}

// Stop stops the worker pool
func (wp *WorkerPool) Stop() {
	wp.cancel()
	close(wp.taskQueue)
	wp.wg.Wait()
}

// Submit submits a task to the worker pool
func (wp *WorkerPool) Submit(task Task) bool {
	select {
	case wp.taskQueue <- task:
		return true
	case <-wp.ctx.Done():
		return false
	}
}

// worker runs a worker goroutine
func (wp *WorkerPool) worker() {
	defer wp.wg.Done()
	for {
		select {
		case task := <-wp.taskQueue:
			if task != nil {
				task.Execute(wp.ctx)
			}
		case <-wp.ctx.Done():
			return
		}
	}
}

