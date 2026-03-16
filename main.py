from src.core.generator import LessonGenerator
from src.core.skill_selector import get_next_skill, get_coverage_report


def main():
    print("\nBantrly Lesson Generator")
    print("=" * 40)

    grade_band = input("Grade Band (K-2 / 3-5 / 6-8 / 9-12)     : ").strip()
    ela_domain = input("ELA Domain (Speaking / Listening / Reading / Writing / Reading → Speaking): ").strip()
    theme      = input("Theme (e.g. Space Exploration)             : ").strip()

    # Preview which skill will be targeted before generation
    next_skill = get_next_skill(grade_band, ela_domain)
    print(f"\nSkill selected  : {next_skill}")

    gen = LessonGenerator(verbose=True)
    lesson = gen.generate(
        grade_band=grade_band,
        ela_domain=ela_domain,
        theme=theme
    )

    print(f"\nLesson saved to : data/generated/{lesson['lesson_id']}.json")

    # Show coverage report after generation
    report = get_coverage_report(grade_band, ela_domain)
    print(f"\nSkill coverage  : {report['covered_count']}/{report['total']} skills covered for {grade_band} {ela_domain}")
    if report['remaining']:
        print(f"Next up         : {report['remaining'][0]}")
    else:
        print("All skills covered — cycling back to least recently used.")


if __name__ == "__main__":
    main()