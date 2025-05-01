import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { FormsModule } from '@angular/forms'; // Import FormsModule
import { CommonModule } from '@angular/common'; // Import CommonModule
import { MatCardModule } from '@angular/material/card'; // Import MatCardModule
import { environment } from 'src/environments/environment';
import { DataService } from 'app/Services/data.service';
// import { jsPDF } from 'jspdf'; // Import jsPDF

interface Ticket {
  TicketNumber: string;
  Prompt: string;
  GeneratedSQL: string;
  IsIntentGenerated: boolean;
  IntentGeneratedData: string;
  ErrorMessage: string;
  TicketStatus: string;
  ResolvedBy?: string; // Include ResolvedBy in the ticket interface
  Priority?: string; // Include Priority in the ticket interface
  selected?: boolean; // Add selected property for bulk actions
}

@Component({
  selector: 'app-ticket-resolver',
  templateUrl: './ticket-resolver.component.html',
  styleUrls: ['./ticket-resolver.component.css'],
  standalone: true,
  imports: [HttpClientModule, FormsModule, CommonModule, MatCardModule] // Ensure all required modules are imported
})
export class TicketResolverComponent implements OnInit {
  tickets: Ticket[] = [];
  filteredTickets: Ticket[] = [];
  paginatedTickets: Ticket[] = []; // Add paginatedTickets array
  searchTerm: string = ''; // Add this property
  loading: boolean = false;
  error: string = '';
  selectedOption: string = '';
  name: string = '';
  ticketNumber: string = '';
  expandedTicketIndex: number | null = null; // Track the expanded ticket index
  teamMembers: string[] = [ 'Arun Kumar Siripuram', 'Avishek Bhagat', 'Vijaya Rishitha Chindukuru', 'Susmitha Kunchavarapu']; // Updated team members
  filterStatus: string = '';
  filterPriority: string = '';
  filterAssignedTo: string = '';
  searchTicketId: string = ''; // Add searchTicketId property
  selectedTickets: Ticket[] = []; // Track selected tickets
  notificationMessage: string = ''; // Property to store the notification message
  notificationTimeout: any; // Timeout reference to clear previous notifications
  rowsPerPage: number = 10; // Default rows per page
  currentPage: number = 1; // Default to the first page
  totalRecords: number = 0; // Total records for pagination

  constructor(private http: HttpClient, private cdr: ChangeDetectorRef,private dataService:DataService) {}

  ngOnInit(): void {
    this.fetchTickets();
    this.filteredTickets = this.tickets; // Initialize filtered tickets
    this.updatePagination(); // Initialize pagination
  }

  fetchTickets(): void {
    this.loading = true;
    this.error = '';
    this.dataService.fetchTickets().subscribe(
      response => {
        console.log('API Response:', response);
        this.loading = false;
        if (response.status === 'success' && response.data) {
          this.tickets = response.data.map((ticket: any) => {
            let parsedData = null;
            if (ticket.IntentGeneratedData) {
              try {
                let sanitizedData = ticket.IntentGeneratedData
                  .toString()
                  .replace(/\n/g, '')
                  .replace(/\r/g, '');
                const optimizedSchemaIndex = sanitizedData.indexOf('"optimized_schema"');
                if (optimizedSchemaIndex !== -1) {
                  sanitizedData = sanitizedData.substring(0, optimizedSchemaIndex - 1).trim();
                  if (sanitizedData.endsWith(',')) {
                    sanitizedData = sanitizedData.slice(0, -1);
                  }
                  sanitizedData += '}';
                
                parsedData = JSON.parse(sanitizedData);
                }
              } catch (e) {
                console.error('Error parsing IntentGeneratedData:', e);
                parsedData = null;
              }
            }

            const mappedStatus = ticket.TicketStatus === 'InProgress' ? 'Pending' : ticket.TicketStatus;

            return {
              ...ticket,
              IntentGeneratedData: parsedData,
              TicketStatus: mappedStatus,
              ResolvedBy: ticket.ResolvedBy
            };
          });
          this.filteredTickets = [...this.tickets]; // Ensure filteredTickets is updated
          this.updatePagination(); // Update pagination after fetching tickets
          this.totalRecords = this.tickets.length; // Set total records for pagination
        } else {
          this.tickets = [];
          this.filteredTickets = []; // Clear filteredTickets if no data
          this.error = 'No tickets found.';
        }
      },
      error => {
        this.loading = false;
        this.error = 'Error fetching ticket details. Please try again.';
        console.error('Error fetching ticket details:', error);
      }
    );
  }

  toggleTicket(index: number): void {
    this.expandedTicketIndex = this.expandedTicketIndex === index ? null : index;
  }

  proceedAction(): void {
    if (!this.name || !this.ticketNumber) {
      this.error = 'Please enter Name and Ticket Number.';
      return;
    }

    let status = '';
    if (this.selectedOption === 'work') {
      status = 'Assigned';
    } else if (this.selectedOption === 'complete') {
      status = 'Resolved';
    } else {
      this.error = 'Please select a valid action.';
      return;
    }

    const payload = {
      ticket_number: this.ticketNumber,
      status: status,
      resolved_by: this.name
    };

    this.loading = true;
    this.dataService.proceedAction(payload).subscribe(
      response => {
        this.loading = false;
        //alert(`Ticket ${this.ticketNumber} has been updated to status "${status}" by ${this.name}.`);
      },
      error => {
        this.loading = false;
        this.error = 'Error updating ticket status. Please try again.';
        console.error('Error updating ticket status:', error);
      }
    );
  }

  applyFilters(): void {
    this.filteredTickets = this.tickets.filter(ticket => {
      const matchesStatus = !this.filterStatus || ticket.TicketStatus === this.filterStatus;
      const matchesAssignedTo = !this.filterAssignedTo || ticket.ResolvedBy === this.filterAssignedTo;
     
      return matchesStatus && matchesAssignedTo;
    });

    this.currentPage = 1; // Reset to the first page after filtering
    this.updatePagination(); // Update paginatedTickets
  }

  sortTickets(column: keyof Ticket, direction: string): void {
    const modifier = direction === 'desc' ? -1 : 1;
    this.filteredTickets = [...this.filteredTickets].sort((a, b) => {
      const valueA = a[column] !== undefined && a[column] !== null ? a[column] : ''; // Explicit check
      const valueB = b[column] !== undefined && b[column] !== null ? b[column] : ''; // Explicit check

      if (valueA < valueB) {
        return -1 * modifier;
      }
      if (valueA > valueB) {
        return 1 * modifier;
      }
      return 0;
    });
    this.updatePagination(); // Update pagination after sorting
  }

  assignTicket(ticket: Ticket): void {
    if (!ticket.ResolvedBy) {
      this.showNotification(`Please select a user to assign Ticket ${ticket.TicketNumber}.`);
      return;
    }

    const payload = {
      ticket_number: ticket.TicketNumber,
      status: 'Assigned',
      resolved_by: ticket.ResolvedBy
    };

    this.dataService.proceedAction(payload).subscribe(
      response => {
        this.showNotification(`Ticket ${ticket.TicketNumber} assigned to ${ticket.ResolvedBy}.`);

        // Update the ticket in the filteredTickets and paginatedTickets arrays
        const ticketIndex = this.filteredTickets.findIndex(t => t.TicketNumber === ticket.TicketNumber);
        if (ticketIndex !== -1) {
          this.filteredTickets[ticketIndex] = { ...ticket, ResolvedBy: ticket.ResolvedBy, TicketStatus: 'Assigned' };
          this.updatePagination(); // Ensure paginatedTickets is updated
        }
      },
      error => {
        console.error('Error assigning ticket:', error);
        this.showNotification(`Failed to assign Ticket ${ticket.TicketNumber}. Please try again.`);
      }
    );
  }

  resolveTicket(ticket: Ticket): void {
    if (!ticket.ResolvedBy) {
      ticket.ResolvedBy = this.teamMembers[0]; // Default to the first team member
    }

    const payload = {
      ticket_number: ticket.TicketNumber,
      status: 'Resolved',
      resolved_by: ticket.ResolvedBy
    };

    this.dataService.proceedAction(payload).subscribe(
      response => {
        this.showNotification(`Ticket ${ticket.TicketNumber} resolved by ${ticket.ResolvedBy}.`);

        // Update the ticket in the filteredTickets and paginatedTickets arrays
        const ticketIndex = this.filteredTickets.findIndex(t => t.TicketNumber === ticket.TicketNumber);
        if (ticketIndex !== -1) {
          this.filteredTickets[ticketIndex] = { ...ticket, ResolvedBy: ticket.ResolvedBy, TicketStatus: 'Resolved' };
          this.updatePagination(); // Ensure paginatedTickets is updated
        }
      },
      error => {
        console.error('Error resolving ticket:', error);
        this.showNotification(`Failed to resolve Ticket ${ticket.TicketNumber}. Please try again.`);
      }
    );
  }

  filterRows(): void {
    this.filteredTickets = this.tickets.filter(ticket =>
      ticket.TicketNumber.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
      ticket.Prompt.toLowerCase().includes(this.searchTerm.toLowerCase())
    );
    this.updatePagination(); // Update pagination after filtering rows
  }

  getResolvedTicketsCount(): number {
    // Use filteredTickets if the count should reflect the filtered view
    return this.filteredTickets.filter(ticket => ticket.TicketStatus === 'Resolved').length;
  }

  getAssignedTicketsCount(): number {
    // Count tickets that are assigned
    const assignedTickets = this.filteredTickets.filter(ticket => ticket.ResolvedBy).length;
    // Count tickets that are resolved
    const resolvedTickets = this.filteredTickets.filter(ticket => ticket.TicketStatus === 'Resolved').length;
    // Subtract resolved tickets from assigned tickets and ensure the result is always positive
    return Math.abs(assignedTickets - resolvedTickets);
  }

  getUnassignedTicketsCount(): number {
    // Use filteredTickets if the count should reflect the filtered view
    return this.filteredTickets.filter(ticket => !ticket.ResolvedBy).length;
  }

  // Toggle "Select All" functionality
  toggleSelectAll(event: Event): void {
    const isChecked = (event.target as HTMLInputElement).checked;

    // Only select tickets that are not disabled (e.g., not resolved)
    this.filteredTickets.forEach(ticket => {
      if (ticket.TicketStatus !== 'Resolved') {
        ticket.selected = isChecked;
      }
    });

    // Update the selectedTickets array
    this.selectedTickets = isChecked
      ? this.filteredTickets.filter(ticket => ticket.TicketStatus !== 'Resolved')
      : [];
  }

  // Update selected tickets list
  updateSelectedTickets(ticket: Ticket): void {
    if (ticket.selected) {
      if (!this.selectedTickets.includes(ticket)) {
        this.selectedTickets.push(ticket);
      }
    } else {
      this.selectedTickets = this.selectedTickets.filter(
        selected => selected.TicketNumber !== ticket.TicketNumber
      );
    }
  }

  // Method to show a notification
  showNotification(message: string): void {
    this.notificationMessage = message;

    // Clear any existing timeout to avoid overlapping notifications
    if (this.notificationTimeout) {
      clearTimeout(this.notificationTimeout);
    }

    // Hide the notification after 2 seconds
    this.notificationTimeout = setTimeout(() => {
      this.notificationMessage = '';
    }, 2000);
  }

  // Update applyBulkAssignment to ensure only selected tickets are updated
  applyBulkAssignment(assignedTo: string): void {
    if (!assignedTo) {
      this.showNotification('Please select a user to assign the selected tickets.');
      return;
    }

    const selectedTickets = this.filteredTickets.filter(ticket => ticket.selected);

    if (selectedTickets.length === 0) {
      this.showNotification('No tickets selected for bulk assignment.');
      return;
    }

    selectedTickets.forEach(ticket => {
      ticket.ResolvedBy = assignedTo;

      const payload = {
        ticket_number: ticket.TicketNumber,
        status: 'Assigned',
        resolved_by: assignedTo
      };

      this.dataService.proceedAction(payload).subscribe(
        response => {
          this.showNotification(`Ticket ${ticket.TicketNumber} assigned to ${assignedTo}.`);
        },
        error => {
          console.error(`Error assigning Ticket ${ticket.TicketNumber}:`, error);
          this.showNotification(`Failed to assign Ticket ${ticket.TicketNumber}. Please try again.`);
        }
      );
    });

    this.fetchTickets(); // Refresh the ticket list after bulk assignment
  }

  // Update applyBulkAction to show a single notification
  applyBulkAction(action: string): void {
    if (this.selectedTickets.length > 0) {
      this.selectedTickets.forEach(ticket => {
        ticket.TicketStatus = action;
        this.resolveTicket(ticket); // Call existing resolveTicket method
      });
      this.showNotification(`Applied action "${action}" to ${this.selectedTickets.length} selected ticket(s).`);
    } else {
      this.showNotification('No tickets selected for action.');
    }
  }

  onPageSizeChange(event: Event): void {
    const target = event.target as HTMLSelectElement;
    const newRowsPerPage = parseInt(target.value, 10);

    // Calculate the index of the first row of the current page
    const firstRowIndex = (this.currentPage - 1) * this.rowsPerPage;

    // Update rowsPerPage
    this.rowsPerPage = newRowsPerPage;

    // Calculate the new page number where the first row is located
    this.currentPage = Math.floor(firstRowIndex / this.rowsPerPage) + 1;

    // Update pagination
    this.updatePagination();
  }

  isPageSizeDisabled(pageSize: number): boolean {
    const remainingRecords = this.totalRecords - (this.currentPage - 1) * this.rowsPerPage;
    return remainingRecords < pageSize;
  }

  updatePagination(): void {
    const startIndex = (this.currentPage - 1) * this.rowsPerPage;
    const endIndex = startIndex + this.rowsPerPage;
    this.paginatedTickets = this.filteredTickets.slice(startIndex, endIndex); // Update paginatedTickets
  }

  getTotalPages(): number {
    return Math.ceil(this.filteredTickets.length / this.rowsPerPage);
  }

  getPageNumbers(): number[] {
    return Array.from({ length: this.getTotalPages() }, (_, i) => i + 1);
  }

  goToPage(page: number): void {
    if (page >= 1 && page <= this.getTotalPages()) {
      this.currentPage = page;
      this.updatePagination();
    }
  }
}
