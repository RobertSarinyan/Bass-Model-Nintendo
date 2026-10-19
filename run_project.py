import analyze_bass
import forecast_switch2
import verify_project
import write_report
import build_report


def main():
    analyze_bass.main()
    forecast_switch2.main()
    verify_project.verify_numbers()
    write_report.main()
    build_report.build()
    verify_project.verify_report()
    print('Complete. Final report: report/report.pdf')


if __name__ == '__main__':
    main()
