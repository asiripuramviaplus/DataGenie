import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TicketResolverComponent } from './ticket-resolver.component';

describe('TicketResolverComponent', () => {
  let component: TicketResolverComponent;
  let fixture: ComponentFixture<TicketResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TicketResolverComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(TicketResolverComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
