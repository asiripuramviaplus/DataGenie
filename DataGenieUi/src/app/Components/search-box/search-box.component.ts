// import { environment } from '/Products/CTRMA/CTRMA_NEW/CTRMAMETRICS/DataGenieUi/src/environments/environment';
import { environment } from 'src/environments/environment';
import { saveAs } from 'file-saver';
// search-box.component.ts
import { Component, ElementRef, OnInit, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import {
  HttpClient,
  HttpHeaders,
  HttpClientModule,
  provideHttpClient
} from '@angular/common/http';
import { ModalComponent } from './fullscreen.component';
import { RouterModule } from '@angular/router';
import hljs from 'highlight.js';
import { DataService } from 'app/Services/data.service';

export interface ApiResponse {
  generated_sql: string;
  generation_time: string;
  generated_summary: string; // Add generated_summary to the interface
  generated_recommendations: string;
  total_records: number;
  query_complexity: {
    complexity_score: number;
    complexity_level: string;
    complexity_factors: {
      query_length: number;
      join_count: number;
      subquery_count: number;
      select_all: boolean;
    };
  };
  validation_warnings: string[];
  missing_tables: string[];
  validation_flag: boolean;
  execution_result: QueryResult;
  ticket_number?: string;
}

interface QueryResult {
  columns: string[];
  rows: any[];
  message: string;
  message_code: number;
  execution_time: string;
  query_status: string;
  row_count: number;
  data_size_mb: number;
  total_records: number;
  ticket_number?: string;
}

@Component({
  selector: 'app-search-box',
  standalone: true,
  imports: [
    FormsModule,
    CommonModule,
    HttpClientModule,
    ModalComponent,
    RouterModule,
  ],
  templateUrl: './search-box.component.html',
  styleUrls: ['./search-box.component.css'],
})
export class SearchBoxComponent implements OnInit {
  dataReceived: boolean = false;
  query: string = '';
  generatedSql: string = '';
  generationTime: string = '';
  executionTime: string = '';
  generatedSummary: string = ''; // Add a property to store the generated summary
  generatedRecommendations: string = ''; // Add a property to store the generated recommendations
  complexityLevel: string = '';
  validationWarnings: string[] = [];
  // queryResult: QueryResult | null = null;
  resultColumns: string[] = [];
  isLoading: boolean = false;
  filteredRows: any[] = [];
  sortDirection: string = '';
  sortColumn: string = '';
  error: string = '';
  isQuerySubmitted: boolean = false; // Add a flag to track if the query has been submitted
  isQueryNotEmpty: boolean = false; // Add a flag to track if the query is not empty

  examplePrompts: string[] = [];
  allPrompts: string[] = [];
  showPrompts: boolean = true; // Add a flag to control the visibility of prompts
  isModalOpen = false; //newwwwwwwwwww
  // pagedRows: any[] = [];
  // currentPage: number = 1;
  rowsPerPage: number = 10;
  // totalPages: number = 1;
  // pageSize: number = 10;
  totalRecords: number = 0;
  message: string = '';

  currentPage = 1;
  totalPages = 1;
  pageSize = 10;
  queryResult: any;
  pagedRows: any[] = [];
  offset = 0;
  lastSubmittedQuery: string = ''; // To track the last query submitted
  searchTerm: any;

  // Add these variables on top
  showErrorChatBox: boolean = false;
  errorChatBoxMessage: string = '';
  ticketNumber: string = ''; // Add this property to store the ticket number

  // Chat Window States
  showInteractiveChat: boolean = false;
  chatHistory: { sender: 'bot' | 'user'; message: string }[] = [];
  userInput: string = '';
  currentMode: 'options' | 'ticket' | 'feedback' | 'done' = 'options';
  chatStep: string = 'options';
  userTicketInput: string = '';
  userFeedback: string = '';
  completionMessage: string = '';
  directPageInput: number = 1;
  // @ViewChild('sqlBlock', { static: false }) sqlBlock!: ElementRef;

  private socket: WebSocket | null = null;

  constructor(private http: HttpClient, private dataService: DataService) {}
  // @ViewChild('sqlBlock') sqlBlock!: ElementRef;

  // ngAfterViewInit() {
  //   if (this.sqlBlock) {
  //     hljs.highlightElement(this.sqlBlock.nativeElement);
  //   }
  // }

  // ✅ Chatbox Variables
  showChatBox: boolean = false;
  chatBoxMessage: string = '';
  chatBoxType: string = ''; // 'success' or 'error'

  ngOnInit() {
    this.connectToWebSocket();
    this.loadPrompts();
    this.filteredRows = this.pagedRows;
  }

  connectToWebSocket() {
    // this.socket = new WebSocket('ws://your-backend-server:8000/ws/notifications');
    // this.socket = new WebSocket('ws://127.0.0.1:8000/ws/notifications');
    this.socket = new WebSocket(
      `${environment.apiUrl.replace('http', 'ws')}/ws/notifications`
    );

    this.socket.onmessage = (event) => {
      const message = event.data;
      this.showChat(message, 'success'); // Display the message in the chat box
    };

    this.socket.onclose = () => {
      console.warn('WebSocket connection closed. Reconnecting...');
      setTimeout(() => this.connectToWebSocket(), 5000); // Reconnect after 5 seconds
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  // ✅ Chatbox trigger method
  showChat(message: string, type: 'success' | 'error' | 'warning') {
    this.chatBoxMessage = message;
    this.chatBoxType = type;
    this.showChatBox = true;

    // Auto-hide after 2 seconds
    setTimeout(() => {
      this.showChatBox = false;
    }, 6000);
  }

  showErrorChat() {
    if (!this.ticketNumber) {
      console.warn(
        'Ticket number is missing. Error chat will not be displayed.'
      );
      return;
    }

    this.errorChatBoxMessage = `We’re sorry! An error occurred. 
Ticket No: ${this.ticketNumber}
Our team has raised a ticket and is looking into this. 
Thank you for your patience.`;
    this.showErrorChatBox = true;

    // Auto-close after 10 seconds
    setTimeout(() => {
      this.showErrorChatBox = false;
    }, 10000);
  }

  // Toggle Chat Box
  toggleInteractiveChat() {
    this.showInteractiveChat = !this.showInteractiveChat;
    this.chatHistory = [];
    this.currentMode = 'options';
    this.chatHistory.push({
      sender: 'bot',
      message: 'Hi! How can I assist you today? 😊',
    });
  }

  chooseOption(option: string) {
    if (option === 'ticket') {
      this.chatHistory.push({
        sender: 'user',
        message: 'I want to enquire about a ticket.',
      });
      this.chatHistory.push({
        sender: 'bot',
        message: 'Please enter your Ticket Number:',
      });
      this.currentMode = 'ticket';
    } else {
      this.chatHistory.push({
        sender: 'user',
        message: 'I want to give feedback.',
      });
      this.chatHistory.push({
        sender: 'bot',
        message: 'Please write your feedback below:',
      });
      this.currentMode = 'feedback';
    }
  }

  // sendUserMessage() {
  //   if (!this.userInput.trim()) return;
  //   this.chatHistory.push({ sender: 'user', message: this.userInput });

  //   if (this.currentMode === 'ticket') {
  //     this.chatHistory.push({ sender: 'bot', message: `✅ Ticket ${this.userInput} is being processed. We'll update you soon.` });
  //   } else if (this.currentMode === 'feedback') {
  //     this.chatHistory.push({ sender: 'bot', message: '✅ Thank you for your valuable feedback!' });
  //   }

  //   this.userInput = '';
  //   this.currentMode = 'done';
  // }
  sendUserMessage() {
    if (!this.userInput.trim()) return;
    console.log('User input received:', this.userInput);

    this.chatHistory.push({ sender: 'user', message: this.userInput });

    if (this.currentMode !== 'ticket') return;

    console.log('Ticket mode activated. Fetching details for:', this.userInput);
    this.chatHistory.push({
      sender: 'bot',
      message: `🔍 <b>Checking details for ticket ${this.userInput}...</b>`,
    });

    // this.http
    //   .get<any>(
    //     `${environment.apiUrl}/get-ticket-status?ticket_number=${this.userInput}`
      // )
      this.dataService.sendUserMessage(this.userInput)
      .subscribe(
        (response) => {
          console.log('API response received:', response);

          if (!response || response.status === 'not_found') {
            console.warn('Invalid ticket number.');
            this.chatHistory.push({
              sender: 'bot',
              message: `⚠️ <b>No details found for ticket ${this.userInput}.</b><br>Please check and try again.`,
            });
            return;
          }

          const { TicketNumber, TicketId, Status, ResolvedBy, ResolutionDate } =
            response;
          const formattedMessage =
            Status === 'Resolved'
              ? `✅ <b>Good news!</b><br><br><b>Ticket:</b> ${TicketNumber}<br><b>Resolved By:</b> ${ResolvedBy}<br><b>Resolution Date:</b> ${new Date(
                  ResolutionDate
                ).toLocaleString()}`
              : `⏳ <b>Your ticket is in progress.</b><br><br><b>Ticket:</b> ${TicketNumber}<br><b>Status:</b> ${Status}<br><br>Our team is working on it! 🚀`;

          console.log('Formatted bot message:', formattedMessage);
          this.chatHistory.push({ sender: 'bot', message: formattedMessage });
        },
        (error) => {
          console.error('Error fetching ticket details:', error);
          this.chatHistory.push({
            sender: 'bot',
            message: `❌ <b>Oops! Something went wrong.</b><br>Please try again later.`,
          });
        }
      );

    this.userInput = '';
  }

  // Handle Option Selection
  selectOption(option: string) {
    if (option === 'ticket') {
      this.chatStep = 'ticketInput';
    } else if (option === 'feedback') {
      this.chatStep = 'feedbackInput';
    }
  }

  // Handle Ticket Submission
  submitTicket() {
    if (this.userTicketInput.trim() === '') {
      this.completionMessage = '⚠️ Please enter a valid ticket number.';
    } else {
      // (Optional) Add logic to fetch ticket status here
      this.completionMessage = `✅ Ticket ${this.userTicketInput} is being processed. Our team will update you shortly.`;
      this.chatStep = 'completed';
    }
  }

  // Handle Feedback Submission
  submitFeedback() {
    if (this.userFeedback.trim() === '') {
      this.completionMessage = '⚠️ Feedback cannot be empty.';
    } else {
      // (Optional) Store feedback logic
      this.completionMessage = '✅ Thank you for your valuable feedback!';
      this.chatStep = 'completed';
    }
  }

  async loadPrompts() {
    try {
      const response = await this.http
        .get<{ prompts: string[] }>('/assets/example-prompts.json')
        .toPromise();
      if (response && response.prompts) {
        this.allPrompts = response.prompts;
        this.refreshPrompts();
      }
    } catch (error) {
      console.error('Error loading prompts:', error);
    }
  }

  refreshPrompts() {
    this.examplePrompts = [];
    const shuffledPrompts = this.allPrompts.sort(() => 0.5 - Math.random());
    this.examplePrompts = shuffledPrompts.slice(0, 3);
  }

  setQuery(prompt: string) {
    this.query = prompt;
    this.onQueryChange();
    this.generateAndExecuteSql();
  }

  onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter') {
      if (!event.shiftKey) {
        event.preventDefault(); // Prevent new line insertion
        this.generateAndExecuteSql(); // Call the form submission function
      }
    }
  }

  onQueryChange() {
    // Clear previous data when new query is typed
    // If user is typing a completely new query (different from last submitted)
    if (this.query.trim() !== this.lastSubmittedQuery.trim()) {
      // Clear previous results
      this.dataReceived = false;
      this.generatedSql = '';
      this.generatedSummary = '';
      this.generatedRecommendations = '';
      this.generationTime = '';
      this.executionTime = '';
      this.queryResult = null;
      this.resultColumns = [];
      this.pagedRows = [];
      this.message = '';
      this.totalPages = 0;
      this.currentPage = 1;
      this.error = '';
      this.ticketNumber = '';
      this.directPageInput = 1;
    }
    // this.isQueryNotEmpty = !!this.query;
    this.isQueryNotEmpty = this.query.trim().length > 0;
    if (!this.query) {
      this.showPrompts = true;
      this.isQuerySubmitted = false;
    }
  }

  copyToClipboard(elementRef: ElementRef) {
    if (elementRef) {
      const textArea = document.createElement('textarea');
      textArea.value = elementRef.nativeElement.innerText;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      alert('SQL copied to clipboard!');
    }
  }

  toggleModal() {
    this.isModalOpen = !this.isModalOpen;
  }
  updatePagination() {
    if (this.queryResult) {
      // Calculate the total number of pages
      this.totalPages = Math.ceil(
        this.queryResult.rows.length / this.rowsPerPage
      );

      // Calculate the start and end indexes for the current page
      const startIndex = (this.currentPage - 1) * this.rowsPerPage;
      const endIndex = startIndex + this.rowsPerPage;

      // Slice the rows array to get only the rows for the current page
      this.pagedRows = this.queryResult.rows.slice(startIndex, endIndex);
      console.log('CurrentPage:', this.currentPage);
      this.filterRows();
    }
  }

  async generateAndExecuteSql() {
    console.log('generateAndExecuteSql called');
    this.isLoading = true;
    this.error = '';
    this.queryResult = null;
    this.pagedRows = [];
    this.resultColumns = [];
    this.generatedRecommendations = '';
    this.generatedSummary = '';
    this.message = '';
    this.currentPage = 1;
    this.offset = 0;
    this.executionTime = '';
    this.ticketNumber = ''; // Reset ticket number

    try {
      const response = await 
this.dataService
        .generateAndExecuteSql(this.query)
        .toPromise();

      console.log('API Response:', response);

      if (response) {
        // Populate common fields
        this.generatedSql = response.generated_sql;
        this.generatedSummary = response.generated_summary;
        this.generatedRecommendations =
          response.generated_recommendations || '';
        this.generationTime = response.generation_time;
        this.message = response.execution_result.message || '';
        this.ticketNumber = response.ticket_number || '';

        // ✅ Save last submitted query
        this.lastSubmittedQuery = this.query.trim();

        // Check if SQL was actually generated and data exists
        const hasValidData =
          response.generated_sql !== 'no query generated' &&
          response.execution_result &&
          (response.execution_result.rows?.length ||
            response.execution_result.message_code === 204);

        if (hasValidData) {
          this.dataReceived = true;
          this.queryResult = response.execution_result;
          this.totalRecords = response.execution_result.total_records;
          this.resultColumns = response.execution_result.columns;
          this.pagedRows = response.execution_result.rows;
          this.executionTime = response.execution_result.execution_time;

          this.currentPage = 1;
          this.totalPages = Math.ceil(this.totalRecords / this.pageSize);
          this.filterRows();
          if (this.pagedRows.length > 0) {
            this.showChat(
              '✅ Success! The data you requested is ready',
              'success'
            );
          } else {
            this.showChat('🔍 No Records found', 'warning');
          }
        } else if (
          response.execution_result?.message_code === 500 &&
          response.execution_result?.query_status === 'Query Failed' &&
          response.ticket_number
        ) {
          this.showChat(
            `❌ Your query failed due to a SQL error. Ticket Number: ${response.ticket_number}`,
            'error'
          );
        } else {
          this.showChat(`⚠️ ${this.generatedRecommendations}`, 'error');
        }
      }
    } catch (error) {
      this.error = 'Error generating SQL or fetching results.';
      console.error('API Error:', error);
      this.showErrorChat(); // Call showErrorChat if an error occurs
    } finally {
      this.isLoading = false;
    }
  }

  fetchResults(offset: number) {
    this.isLoading = true; // Set loading to true
    const requestBody = { sql_query: this.generatedSql };
    this.dataService
      .fetchResults(offset, this.generatedSql, this.pageSize)

      .subscribe(
        (response: any) => {
          this.queryResult = response;
          this.pagedRows = response.rows;
          this.totalRecords = response.total_records;
          this.totalPages = Math.ceil(this.totalRecords / this.pageSize);
          this.currentPage = offset / this.pageSize + 1;
          this.message = response.message;
          this.executionTime = response.execution_time; // Set execution time
          this.ticketNumber = response.execution_result?.ticket_number || ''; // Capture ticket number
          this.dataReceived = true; // Set data received to true
          this.isLoading = false; // Set loading to false
          this.generatedSql = response.generated_sql;
          this.filterRows();
          console.log('Fetched Results:', response);
        },
        (error) => {
          console.error('Pagination Fetch Error:', error);
          this.message = 'Error fetching paginated data.';
          this.isLoading = false; // Set loading to false
        }
      );
  }

  isPaginationDisabled(): boolean {
    return this.totalRecords === 0 || this.pagedRows.length === 0;
  }
  nextPage() {
    if (this.currentPage < this.totalPages) {
      this.offset += this.pageSize;
      this.fetchResults(this.offset);
      this.directPageInput = this.currentPage + 1;
    }
  }

  previousPage() {
    if (this.currentPage > 1) {
      this.offset -= this.pageSize;
      this.fetchResults(this.offset);
      this.directPageInput = this.currentPage - 1;
    }
  }

  getPageNumbers(): number[] {
    const totalNumbers = 5; // Show only 5 pages at a time
    let start = Math.max(1, this.currentPage - 2);
    let end = Math.min(this.totalPages, start + totalNumbers - 1);

    return Array.from({ length: end - start + 1 }, (_, i) => start + i);
  }
  goToPage(event: Event | number) {
    if (typeof event === 'number') {
      this.currentPage = event;
    } else {
      const target = event.target as HTMLSelectElement;
      this.currentPage = Number(target.value);
    }
    this.offset = (this.currentPage - 1) * this.pageSize;
    this.fetchResults(this.offset);
    this.directPageInput = this.currentPage;
  }

  filterRows() {
    if (!this.searchTerm) {
      this.filteredRows = this.pagedRows;
    } else {
      this.filteredRows = this.pagedRows.filter((row) =>
        this.resultColumns.some((column) =>
          row[column]
            .toString()
            .toLowerCase()
            .includes(this.searchTerm.toLowerCase())
        )
      );
    }
  }

  ModelfilterRows(searchTerm: String) {
    // this.searchTerm = (event.target as HTMLInputElement).value;
    this.searchTerm = searchTerm;
    this.filterRows();
  }

  onPageSizeChanged(event: Event): void {
    const selectElement = event.target as HTMLSelectElement;
    this.pageSize = parseInt(selectElement.value, 10);
    this.offset = Math.floor(this.offset / this.pageSize) * this.pageSize;
    this.fetchResults(this.offset);
  }

  isPageSizeDisabled(pageSize: number): boolean {
    // if (this.currentPage === this.totalPages) {
    //   const remainingRecords = this.totalRecords % this.pageSize;
    //   return remainingRecords < pageSize;
    // }
    // return false;
    const remainingRecords =
      this.totalRecords - (this.currentPage - 1) * this.pageSize;
    return remainingRecords < pageSize;
  }

  sortData(column: string, direction: string): void {
    this.sortColumn = column;
    this.sortDirection = direction;
    this.filteredRows = this.filteredRows.sort((a, b) => {
      const modifier = direction === 'desc' ? -1 : 1;
      if (a[column] < b[column]) {
        return -1 * modifier;
      }
      if (a[column] > b[column]) {
        return 1 * modifier;
      }
      return 0;
    });
  }

  calculateRows(query: string): number {
    const lines = query.split('\n').map((line) => line.trim()).length;
    const maxCharsPerLine = 100;
    const totalLines = lines + Math.floor(query.length / maxCharsPerLine);
    return totalLines <= 2 ? 2 : totalLines == 3 ? 3 : 4;
  }

  isCopied: boolean = false;

  copyGeneratedSQL() {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      // Use Clipboard API if available
      navigator.clipboard
        .writeText(this.generatedSql)
        .then(() => {
          this.isCopied = true;
          setTimeout(() => {
            this.isCopied = false;
          }, 3000); // Reset after 3 seconds
        })
        .catch((err) => {
          console.error('Failed to copy text: ', err);
          alert('Failed to copy text. Please try again.');
        });
    } else {
      // Fallback for unsupported browsers
      try {
        const textArea = document.createElement('textarea');
        textArea.value = this.generatedSql;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        this.isCopied = true;
        setTimeout(() => {
          this.isCopied = false;
        }, 3000); // Reset after 3 seconds
      } catch (err) {
        console.error('Fallback: Failed to copy text: ', err);
        alert('Failed to copy text. Please try again.');
      }
    }
  }

  exportToCSV() {
    if (!this.filteredRows || this.filteredRows.length === 0) {
      console.warn('No data to export.');
      return;
    }

    // Convert array of objects to CSV format
    const csvContent = [
      Object.keys(this.filteredRows[0]).join(','), // Header row
      ...this.filteredRows.map((row) =>
        Object.values(row)
          .map((value) => `"${value}"`)
          .join(',')
      ), // Data rows
    ].join('\n');

    // Create a Blob and trigger download
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    saveAs(blob, 'table-data.csv');
  }
}
