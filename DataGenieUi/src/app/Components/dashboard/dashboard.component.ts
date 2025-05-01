import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { CommonModule } from '@angular/common';
import {
  NgxChartsModule,
  Color,
  ScaleType,
  LegendPosition,
} from '@swimlane/ngx-charts';
import { RouterModule } from '@angular/router';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import {
  trigger,
  state,
  style,
  transition,
  animate,
} from '@angular/animations';
import { environment } from 'src/environments/environment';
import { DataService } from 'app/Services/data.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    MatCardModule,
    MatButtonToggleModule,
    CommonModule,
    NgxChartsModule,
    RouterModule,
    HttpClientModule,
    FormsModule,
  ],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css'],
  animations: [
    trigger('animationState', [
      state('open', style({ opacity: 1, transform: 'translateY(0)' })),
      state('closed', style({ opacity: 0, transform: 'translateY(-100%)' })),
      transition('open <=> closed', [animate('300ms ease-in-out')]),
    ]),
  ],
})
export class DashboardComponent implements OnInit {
  searchTerm: string = '';
  ticketNumber: string = '';
  errorMessage: string = '';
  isLoading = false; // Local property to control the spinner
  dExecutions: number = 0;
  totalPrompts: number = 0;
  successfulSQLGenerations: number = 0;
  successfulIntents: number = 0;
  totalExecutions: number = 0;
  successfulExecutions: number = 0;
  failedExecutions: number = 0;
  avgExecutionTime: number = 0;
  avgExecutionTimeSuccess: number = 0;
  avgExecutionTimeFailure: number = 0;
  successRate: string = '';
  intentSuccessRate: string = '';
  turnaroundTime: string = '';
  promptExecutionData: any[] = []; // Data for the line graph
  totalRecordsData: any[] = []; // Data for the bar graph
  executionStats: any[] = []; // Data for the pie chart
  ticketData: { TicketNumber: string; ErrorMessage: string }[] = []; // Array to store ticket data
  sortColumn: string = '';
  sortDirection: string = '';
  successRateColor: string = ''; // Property for success rate card color
  intentSuccessRateColor: string = ''; // Property for intent success rate card color
  containerWidth: number = 500;
  containerHeight: number = 400;
  filteredRows: { TicketNumber: string; ErrorMessage: string }[] = []; // Filtered rows for the table

  constructor(
    private http: HttpClient,
    private cdr: ChangeDetectorRef,
    private dataService: DataService
  ) {}

  ngOnInit(): void {
    window.addEventListener('resize', this.updateChartDimensions.bind(this)); // Update on window resize
    this.isLoading = true; // Show the spinner at the start
    this.getDashboardData();
    this.getTicketData();
  }

  ngAfterViewInit(): void {
    this.updateChartDimensions(); // Set initial dimensions after the view is initialized
  }

  ngOnDestroy(): void {
    window.removeEventListener('resize', this.updateChartDimensions.bind(this)); // Cleanup event listener
  }

  getTicketData(): void {
    this.dataService.getAllErrors().subscribe(
      (response) => {
        console.log('API Response:', response);
        if (response.status === 'success') {
          this.ticketData = response.errors.map((error: any) => ({
            TicketNumber: error.TicketNumber,
            ErrorMessage: error.ErrorMessage,
          }));
        } else {
          console.error('API Error: Unexpected response format', response);
        }
      },
      (error) => {
        console.error('API Error:', error); // Log the error for debugging
      }
    );
  }

  getDashboardData(): void {
    this.isLoading = true;
    console.log('Spinner shown');

    const fallbackTimeout = setTimeout(() => {
      this.isLoading = false;
      console.log('Spinner hidden due to fallback timeout');
    }, 3000); // 3-second fallback timeout

    forkJoin({
      dashboardData: this.dataService.getDashboardData(), // this.http.get<any>(`${environment.apiUrl}/getdashboarddata`),
      // ticketData: this.http.get<any>(`${environment.apiUrl}/get-all-errors`)
      ticketData: this.dataService.getAllErrors(),
    }).subscribe(
      ({ dashboardData, ticketData }) => {
        clearTimeout(fallbackTimeout); // Clear fallback timeout on success
        this.processDashboardData(dashboardData);
        this.processTicketData(ticketData);
        this.isLoading = false;
        console.log('Spinner hidden after API success');
      },
      (error) => {
        clearTimeout(fallbackTimeout); // Clear fallback timeout on error
        console.error('API Error:', error);
        this.isLoading = false;
        console.log('Spinner hidden after API error');
      }
    );
  }

  processDashboardData(response: any): void {
    console.log('API Response:', response); // Log the response for debugging
    if (response.status === 'success') {
      const resultSets = response.result_sets;

      // Extract data from result sets
      if (resultSets.length > 0 && resultSets[0].rows.length > 0) {
        const metrics = resultSets[0].rows[0];
        this.totalPrompts = parseInt(metrics.TotalPrompts, 10);
        this.successfulSQLGenerations = parseInt(
          metrics.SuccessfulSQLGenerations,
          10
        );
        this.successfulIntents = parseInt(metrics.SuccessfulIntents, 10);
      }

      if (resultSets.length > 1 && resultSets[1].rows.length > 0) {
        const executions = resultSets[1].rows[0];
        this.totalExecutions = parseInt(executions.TotalExecutions, 10);
        this.successfulExecutions = parseInt(
          executions.SuccessfulExecutions,
          10
        );
        this.failedExecutions = parseInt(executions.FailedExecutions, 10);

        // Update executionStats for the pie chart
        this.executionStats = [
          { name: 'Successful Executions', value: this.successfulExecutions },
          { name: 'Failed Executions', value: this.failedExecutions },
        ];
      }

      if (resultSets.length > 2 && resultSets[2].rows.length > 0) {
        const avgTimes = resultSets[2].rows[0];
        this.avgExecutionTime = parseFloat(avgTimes.AvgExecutionTime);
        this.avgExecutionTimeSuccess = parseFloat(
          avgTimes.AvgExecutionTime_Success
        );
        this.avgExecutionTimeFailure = parseFloat(
          avgTimes.AvgExecutionTime_Failure
        );
      }

      if (resultSets.length > 3 && resultSets[3].rows.length > 0) {
        const promptData = resultSets[3].rows;

        this.promptExecutionData = [
          {
            name: 'SQL Generation Time',
            series: promptData.map((row: any) => ({
              name: row.Prompt,
              value: parseFloat(row.SqlGenerationTime), // Convert to number
            })),
          },
          {
            name: 'Execution Time',
            series: promptData.map((row: any) => ({
              name: row.Prompt,
              value: parseFloat(row.ExecutionTime), // Convert to number
            })),
          },
        ];

        this.totalRecordsData = [
          {
            name: 'Total Records',
            series: promptData.map((row: any) => ({
              name: row.Prompt,
              value: parseFloat(row.TotalRecords), // Convert to number
            })),
          },
        ];
      }

      console.log('Prompt Execution Data:', this.promptExecutionData);

      this.calculateSuccessRates();
      this.calculateTurnaroundTime();
    } else {
      console.error('API Error: Unexpected response format', response);
    }
  }

  processTicketData(response: any): void {
    console.log('API Response:', response);
    if (response.status === 'success') {
      this.ticketData = response.errors.map((error: any) => ({
        TicketNumber: error.TicketNumber,
        ErrorMessage: error.ErrorMessage,
      }));
      this.filteredRows = [...this.ticketData]; // Initialize filtered rows
    } else {
      console.error('API Error: Unexpected response format', response);
    }
  }
  transform: 'translateY(0)' = 'translateY(0)'; // Initial state for animation

  filterRows(): void {
    if (!this.searchTerm) {
      // Restore the original table data when the search box is cleared
      this.filteredRows = [...this.ticketData];
    } else {
      // Filter rows based on the search term
      const searchTermLower = this.searchTerm.toLowerCase();
      this.filteredRows = this.ticketData.filter((row) =>
        Object.values(row).some((value) =>
          value.toString().toLowerCase().includes(searchTermLower)
        )
      );
    }
  }

  calculateSuccessRates(): void {
    if (this.totalExecutions > 0) {
      this.successRate =
        ((this.successfulExecutions / this.totalExecutions) * 100).toFixed(2) +
        '%';
      this.successRateColor = this.getColorBasedOnRate(
        this.successfulExecutions / this.totalExecutions
      );
    } else {
      this.successRate = 'N/A';
      this.successRateColor = '#d3d3d3'; // Default gray color
    }

    if (this.totalPrompts > 0) {
      this.intentSuccessRate =
        ((this.successfulIntents / this.totalPrompts) * 100).toFixed(2) + '%';
      this.intentSuccessRateColor = this.getColorBasedOnRate(
        this.successfulIntents / this.totalPrompts
      );
    } else {
      this.intentSuccessRate = 'N/A';
      this.intentSuccessRateColor = '#d3d3d3'; // Default gray color
    }
  }

  getColorBasedOnRate(rate: number): string {
    if (rate >= 0.8) {
      return '#4caf50'; // Green for high success rates
    } else if (rate >= 0.5) {
      return '#ffbf00'; // Yellow for medium success rates
    } else {
      return '#f44336'; // Red for low success rates
    }
  }

  calculateTurnaroundTime(): void {
    if (this.totalExecutions > 0) {
      this.turnaroundTime = this.avgExecutionTime.toFixed(2) + ' seconds';
    } else {
      this.turnaroundTime = 'N/A';
    }
  }

  sortTicketData(
    column: keyof (typeof this.ticketData)[0],
    direction: string
  ): void {
    const modifier = direction === 'desc' ? -1 : 1;
    this.filteredRows = [...this.filteredRows].sort((a, b) => {
      if (a[column] < b[column]) {
        return -1 * modifier;
      }
      if (a[column] > b[column]) {
        return 1 * modifier;
      }
      return 0;
    });
  }

  // Chart customization options

  view: [number, number] = [0, 0]; // Chart size initialized dynamically

  updateChartDimensions(): void {
    const container = document.querySelector('.line-chart-container');
    if (container) {
      const containerWidth = container.clientWidth;
      const containerHeight = container.clientHeight;

      // Adjust dimensions to account for padding or margins and set a minimum height
      const adjustedWidth = containerWidth - 20; // Example adjustment
      const adjustedHeight = Math.max(containerHeight - 20, 300); // Ensure a minimum height of 300px

      this.view = [Math.max(adjustedWidth, 0), adjustedHeight];

      // Trigger change detection to avoid ExpressionChangedAfterItHasBeenCheckedError
      this.cdr.detectChanges();
    }
  }

  legendPosition: LegendPosition = LegendPosition.Below; // Set legend position to 'below'
  legendPosition1: LegendPosition = LegendPosition.Right; // Use a valid position like 'Right'

  // Color Scheme (Blue for SQL Generation, Green for Execution, Red for Turnaround)
  linecolorScheme: Color = {
    domain: ['#008FFB', '#00E396', '#FF4560'],
    group: ScaleType.Ordinal,
    selectable: true,
    name: 'custom',
  };

  piecolorScheme: Color = {
    domain: ['#5cb85c', '#Cc0202', '#008FFB'],
    group: ScaleType.Ordinal,
    selectable: true,
    name: 'custom',
  };

  line_showlegend = false;
  // Chart Settings
  showLegend = true;
  showLabels = true;
  animations = true;
  xAxis = true;
  yAxis = true;
  timeline = true;
  autoScale = true;
}
