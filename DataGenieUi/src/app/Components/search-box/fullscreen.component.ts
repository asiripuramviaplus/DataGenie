import { Component, Input, Output, EventEmitter, Injectable } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { BehaviorSubject } from 'rxjs'; // Import BehaviorSubject

@Injectable({
  providedIn: 'root'
})
export class LoadingService {
  private loadingSubject = new BehaviorSubject<boolean>(false);
  isLoading = this.loadingSubject.asObservable();

  showLoading() {
    this.loadingSubject.next(true);
  }

  hideLoading() {
    this.loadingSubject.next(false);
  }
}

@Component({
  selector: 'app-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div *ngIf="isOpen" class="modal-overlay" (click)="close()">
      <div class="modal-content" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <p>{{title}}</p>
          <div class="model-header-right">
            <div class="search-box">
            <!-- "search-icon"> -->
              <i class="fas fa-search"></i>
            <!-- </span> -->
            <input 
              type="text" 
              placeholder="Search..." 
              class="search-input" [(ngModel)]="searchTerm" 
              (ngModelChange)="search()" />
            </div>  
              <button class="close-button" (click)="close()">
                <i class="bi bi-x-lg"></i>
              </button>
            </div>
        </div>
        <div class="modal-body">
          <ng-content></ng-content>
        </div>
        <div *ngIf="loadingService.isLoading | async" class="loading-overlay">
          <div class="spinner"></div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .modal-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background-color: rgba(0, 0, 0, 0.5);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 1000;
    }

    .modal-content {
      padding: 32px;
      background-color: white;
      border-radius: 8px;
      width: 95%;
      height: 90%;
      max-width: 1800px;
      position: relative;
      display: flex;
      flex-direction: column;
      gap: 30px;
    }

    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .modal-header p {
      margin: 0;
      font-size: 26px;
      font-weight: 600;
    }

    .model-header-right {
      display: flex;
      align-items: center;
    }

    .close-button {
      display: flex;
      align-items: center;
      padding: 4px 8px;
      gap: 8px;
      background-color: white;
      color: black;
      border: 1px solid #d0d3d8;
      border-radius: 6px; /* Slightly rounded */
      cursor: pointer;
      font-size: 12px;
      transition: font-size 0.2s;
    }
    
    .close-button:hover {
      font-size: 16px;
      color: #014990;
    }

    .modal-body {
      overflow: auto;
      flex-grow: 1;
    }
        
    .search-box {
      display: flex;
      align-items: center;
      gap: 0.3rem;
      padding: 4px 8px; /* More compact padding */
      background: white;
      width: 300px; /* Reduced width */
      border-radius: 15px; /* More rounded */
      border: 1px solid #ddd; /* Light gray border */
      box-shadow: none;
      height: 28px; /* Smaller height */
      margin-right: 15px;
    }

    .search-icon {
      font-size: 12px; /* Smaller icon */
      color: #5b6871; /* Lighter gray icon color */
      margin-right: 4px;
      background: #33a6b8; /* Light blue background */
      padding: 4px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 20px;
      height: 20px;
    }

    .search-input {
      border: none;
      background: transparent;
      font-size: 12px; /* Smaller text */
      outline: none;
      flex: 1;
      color: #5b6871; /* Light gray text */
    }

    .search-box::after {
      display: none; /* Removed underline */
    }

    .loading-overlay {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(255, 255, 255, 0.8);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 1001;
    }

    .spinner {
      border: 4px solid rgba(0, 0, 0, 0.1);
      border-top: 4px solid #014990;
      border-radius: 50%;
      width: 40px;
      height: 40px;
      animation: spin 1s linear infinite;
    }

    @keyframes spin {
      0% {
        transform: rotate(0deg);
      }
      100% {
        transform: rotate(360deg);
      }
    }
  `]
})
export class ModalComponent {
  @Input() isOpen = false;
  @Input() title = '';
  @Output() closeModal = new EventEmitter<void>();
  @Output() searchEvent = new EventEmitter<string>();

  searchTerm = '';

  constructor(public loadingService: LoadingService) {} // Inject the service

  close() {
    this.closeModal.emit();
  }

  search() {
    this.searchEvent.emit(this.searchTerm);
    this.loadingService.showLoading(); // Show loading when search is triggered
  }
}
 